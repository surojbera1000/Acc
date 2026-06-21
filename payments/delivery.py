"""Account delivery service with auto-refund on failure."""
import logging
from typing import Optional, Dict

from database import Database
from config import SUPPORT_CONTACT, ADMIN_IDS, CURRENCY_SYMBOL

logger = logging.getLogger(__name__)


class DeliveryService:
    """Handles account delivery with automatic refund on failure."""

    def __init__(self, db: Database):
        self.db = db

    async def deliver_account(self, order_id: int, user_id: int,
                               account_id: int, bot) -> Dict:
        """
        Attempt to deliver an account to a user.

        Returns a dict with:
            - success: bool
            - message: str (delivery text or error message)
            - refunded: bool (True if auto-refund was applied)
        """
        try:
            # Get account details
            account = await self.db.get_account(account_id)
            if not account:
                raise DeliveryError("Account not found in database")

            if account["status"] != "sold" or account["sold_to"] != user_id:
                raise DeliveryError("Account ownership mismatch")

            # Get country info
            country = await self.db.get_country(account["country_id"])
            if not country:
                raise DeliveryError("Country information not found")

            # Build delivery message
            delivery_text = (
                f"✅ <b>Account Delivered!</b>\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 <b>Order #{order_id}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🌍 Country: <b>{country['flag']} {country['name']}</b>\n"
                f"📱 Phone: <code>{account['phone_number']}</code>\n"
            )

            if account.get("otp"):
                delivery_text += f"🔑 OTP: <code>{account['otp']}</code>\n"

            if account.get("two_fa"):
                delivery_text += f"🔐 2FA: <code>{account['two_fa']}</code>\n"

            if account.get("session"):
                delivery_text += (
                    f"\n💾 <b>Session string</b> (log in with this to stay logged in):\n"
                    f"<code>{account['session']}</code>\n"
                )

            delivery_text += (
                f"\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ <i>Save this information securely!</i>"
            )

            # Mark order as completed
            await self.db.complete_order(order_id)

            # Send delivery message to user
            try:
                await bot.send_message(user_id, delivery_text, parse_mode="HTML")
            except Exception as send_error:
                logger.error(f"Failed to send delivery message to {user_id}: {send_error}")
                # Even if message fails, the order is complete
                # User can check order history

            logger.info(f"Delivery successful: Order #{order_id}, Account #{account_id}, User {user_id}")

            return {
                "success": True,
                "message": delivery_text,
                "refunded": False
            }

        except (DeliveryError, Exception) as e:
            logger.error(f"Delivery failed: Order #{order_id}, Error: {e}")
            return await self._handle_failed_delivery(order_id, user_id, account_id, str(e), bot)

    async def _handle_failed_delivery(self, order_id: int, user_id: int,
                                        account_id: int, reason: str, bot) -> Dict:
        """Handle a failed delivery with automatic refund."""
        try:
            # Get order details for refund amount
            order = await self.db.get_order(order_id)
            if not order:
                logger.error(f"Cannot refund - order #{order_id} not found")
                return {
                    "success": False,
                    "message": "Delivery and refund both failed. Contact support.",
                    "refunded": False
                }

            amount = order["amount"]

            # Mark order as failed
            await self.db.fail_order(order_id, reason)

            # Refund the user's balance
            new_balance = await self.db.update_balance(user_id, amount, "add")

            # Create refund transaction
            tx_id = await self.db.create_transaction(
                user_id, "refund", amount,
                description=f"Auto-refund: delivery failed for Order #{order_id}",
                reference=f"REFUND-{order_id}"
            )
            await self.db.complete_transaction(tx_id, new_balance)

            # Mark order as refunded
            await self.db.refund_order(order_id, f"Auto-refund: {reason}")

            # Make account available again
            await self.db.mark_account_available(account_id)

            # Notify user about refund
            refund_text = (
                f"⚠️ <b>Delivery Issue - Auto Refund</b>\n\n"
                f"We encountered a technical issue delivering your order.\n\n"
                f"💰 <b>Refund: {CURRENCY_SYMBOL}{amount:.2f}</b>\n"
                f"👛 New Balance: <b>{CURRENCY_SYMBOL}{new_balance:.2f}</b>\n\n"
                f"Your funds have been automatically returned to your wallet.\n"
                f"You can try purchasing again or contact support.\n\n"
                f"📩 Support: {SUPPORT_CONTACT}"
            )

            try:
                await bot.send_message(user_id, refund_text, parse_mode="HTML")
            except Exception:
                pass

            # Notify admins about failed delivery
            admin_text = (
                f"🚨 <b>Failed Delivery Alert</b>\n\n"
                f"Order: #{order_id}\n"
                f"User: {user_id}\n"
                f"Account: #{account_id}\n"
                f"Amount: {CURRENCY_SYMBOL}{amount:.2f}\n"
                f"Reason: {reason}\n\n"
                f"✅ Auto-refund applied successfully.\n"
                f"Account returned to stock."
            )

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, admin_text, parse_mode="HTML")
                except Exception:
                    pass

            logger.info(
                f"Auto-refund applied: Order #{order_id}, "
                f"Amount {amount}, User {user_id}"
            )

            return {
                "success": False,
                "message": refund_text,
                "refunded": True
            }

        except Exception as refund_error:
            logger.critical(
                f"CRITICAL: Refund failed for Order #{order_id}: {refund_error}"
            )

            # Emergency notification to admins
            emergency_text = (
                f"🚨🚨 <b>CRITICAL: REFUND FAILED</b> 🚨🚨\n\n"
                f"Order: #{order_id}\n"
                f"User: {user_id}\n"
                f"Account: #{account_id}\n"
                f"Error: {refund_error}\n\n"
                f"⚠️ Manual intervention required!"
            )

            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, emergency_text, parse_mode="HTML")
                except Exception:
                    pass

            return {
                "success": False,
                "message": "Critical error. Support has been notified.",
                "refunded": False
            }


class DeliveryError(Exception):
    """Custom exception for delivery failures."""
    pass
