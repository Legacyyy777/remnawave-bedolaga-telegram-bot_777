import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import WelcomeText

logger = logging.getLogger(__name__)

WELCOME_TEXT_KEY = "welcome_text"

async def get_active_welcome_text(db: AsyncSession) -> Optional[str]:
    result = await db.execute(
        select(WelcomeText)
        .where(WelcomeText.is_active == True)
        .where(WelcomeText.is_enabled == True) 
        .order_by(WelcomeText.updated_at.desc())
    )
    welcome_text = result.scalar_one_or_none()
    
    if welcome_text:
        return welcome_text.text_content
    
    return None

async def get_current_welcome_text_settings(db: AsyncSession) -> dict:
    result = await db.execute(
        select(WelcomeText)
        .where(WelcomeText.is_active == True)
        .order_by(WelcomeText.updated_at.desc())
    )
    welcome_text = result.scalar_one_or_none()
    
    if welcome_text:
        return {
            'text': welcome_text.text_content,
            'is_enabled': welcome_text.is_enabled,
            'id': welcome_text.id
        }
    
    return {
        'text': await get_current_welcome_text_or_default(),
        'is_enabled': True,
        'id': None
    }

async def toggle_welcome_text_status(db: AsyncSession, admin_id: int) -> bool:
    try:
        result = await db.execute(
            select(WelcomeText)
            .where(WelcomeText.is_active == True)
            .order_by(WelcomeText.updated_at.desc())
        )
        welcome_text = result.scalar_one_or_none()
        
        if welcome_text:
            welcome_text.is_enabled = not welcome_text.is_enabled
            welcome_text.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(welcome_text)
            
            status = "включен" if welcome_text.is_enabled else "отключен"
            logger.info(f"Приветственный текст {status} администратором {admin_id}")
            return welcome_text.is_enabled
        else:
            default_text = await get_current_welcome_text_or_default()
            new_welcome_text = WelcomeText(
                text_content=default_text,
                is_active=True,
                is_enabled=True,
                created_by=admin_id
            )
            
            db.add(new_welcome_text)
            await db.commit()
            await db.refresh(new_welcome_text)
            
            logger.info(f"Создан и включен дефолтный приветственный текст администратором {admin_id}")
            return True
            
    except Exception as e:
        logger.error(f"Ошибка при переключении статуса приветственного текста: {e}")
        await db.rollback()
        return False

async def set_welcome_text(db: AsyncSession, text_content: str, admin_id: int) -> bool:
    try:
        current_settings = await get_current_welcome_text_settings(db)
        current_enabled_status = current_settings.get('is_enabled', True)
        
        await db.execute(
            update(WelcomeText).values(is_active=False)
        )
        
        new_welcome_text = WelcomeText(
            text_content=text_content,
            is_active=True,
            is_enabled=current_enabled_status, 
            created_by=admin_id
        )
        
        db.add(new_welcome_text)
        await db.commit()
        await db.refresh(new_welcome_text)
        
        logger.info(f"Установлен новый приветственный текст администратором {admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при установке приветственного текста: {e}")
        await db.rollback()
        return False

async def get_current_welcome_text_or_default() -> str:
    return (
        f"Привет, {{user_name}}! 🎁 3 дней VPN бесплатно! "
        f"Подключайтесь за минуту и забудьте о блокировках. "
        f"✅ До 1 Гбит/с скорость "
        f"✅ Умный VPN — можно не отключать для большинства российских сервисов "
        f"✅ Современные протоколы — максимум защиты и анонимности "
        f"💉 Всего 99₽/мес за 1 устройство "
        f"👇 Жмите кнопку и подключайтесь!"
    )

def replace_placeholders(text: str, user) -> str:
    first_name = getattr(user, 'first_name', None)
    username = getattr(user, 'username', None)
    
    first_name = first_name.strip() if first_name else None
    username = username.strip() if username else None
    
    user_name = first_name or username or "друг"
    display_first_name = first_name or "друг"
    display_username = f"@{username}" if username else (first_name or "друг")
    clean_username = username or first_name or "друг"
    
    replacements = {
        '{user_name}': user_name,
        '{first_name}': display_first_name, 
        '{username}': display_username,
        '{username_clean}': clean_username,
        'Egor': user_name 
    }
    
    result = text
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    return result

async def get_welcome_text_for_user(db: AsyncSession, user) -> str:
    welcome_text = await get_active_welcome_text(db)
    
    if not welcome_text:
        return None
    
    if isinstance(user, str):
        class SimpleUser:
            def __init__(self, name):
                self.first_name = name
                self.username = None
        user = SimpleUser(user)
    
    return replace_placeholders(welcome_text, user)

def get_available_placeholders() -> dict:
    return {
        '{user_name}': 'Имя или username пользователя (приоритет: имя → username → "друг")',
        '{first_name}': 'Только имя пользователя (или "друг" если не указано)',
        '{username}': 'Username с символом @ (или имя если username не указан)',
        '{username_clean}': 'Username без символа @ (или имя если username не указан)'
    }
