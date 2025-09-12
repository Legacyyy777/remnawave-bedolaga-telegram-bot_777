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
        status_icon = {
            "online": "🟢",
            "degraded": "🟡",
            "offline": "🔴",
        }.get(status.get("status"), "🔴")
    except Exception:
        users_online = 0
        status_icon = "🔴"

    admin_text = texts.ADMIN_PANEL.format(
        online_count=users_online,
        status_icon=status_icon,
    )

    await callback.message.edit_text(
        admin_text,
        reply_markup=get_admin_main_keyboard(db_user.language)
    )
    await callback.answer()
