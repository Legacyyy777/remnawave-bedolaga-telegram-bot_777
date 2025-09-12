import logging
from aiogram import Dispatcher, types, F
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User
from app.keyboards.admin import get_admin_main_keyboard
from app.localization.texts import get_texts
from app.utils.decorators import admin_required, error_handler
from app.services.remnawave_service import RemnaWaveService

logger = logging.getLogger(__name__)


@admin_required
@error_handler
async def show_admin_panel(
    callback: types.CallbackQuery,
    db_user: User,
    db: AsyncSession
):
    texts = get_texts(db_user.language)

    try:
        status = await RemnaWaveService().check_panel_health()
        users_online = status.get("users_online", 0)
    except Exception:
        users_online = 0

    admin_text = texts.ADMIN_PANEL.format(online_count=users_online)
    
    await callback.message.edit_text(
        admin_text,
        reply_markup=get_admin_main_keyboard(db_user.language)
    )
    await callback.answer()


def register_handlers(dp: Dispatcher):
    
    dp.callback_query.register(
        show_admin_panel,
        F.data == "admin_panel"
    )
