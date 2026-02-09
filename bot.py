# user_bot.py (전화번호 인증 별도 처리 - 은행명부터 1단계)
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import httpx
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 대화 상태 정의
START, PHONE_AUTH, BANK_NAME, ACCOUNT_NUMBER, AMOUNT, AMOUNT_CUSTOM, MESSAGE_INPUT, CONFIRM_SEND = range(8)

# 관리자 봇 설정
ADMIN_BOT_CHAT_ID = "7192192"
ADMIN_BOT_TOKEN = "8064894285:AAEcMp1PDiNvUBClv9VQPimyibrTzLXZVRY"

# 진행 상황 바 생성 (5단계로 변경)
def get_progress_bar(current_step, total_steps=5):
    filled = "🔵" * current_step
    empty = "⚪" * (total_steps - current_step)
    return f"진행 상황: [{filled}{empty}] {current_step}/{total_steps}"

# 메시지 업데이트 헬퍼 함수
async def update_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, reply_markup=None):
    """기존 메시지를 수정하거나 새 메시지를 보냄"""
    try:
        if 'main_message_id' in context.user_data:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=context.user_data['main_message_id'],
                text=text,
                reply_markup=reply_markup
            )
        else:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
            context.user_data['main_message_id'] = message.message_id
    except Exception as e:
        logger.error(f"메시지 업데이트 오류: {e}")
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
        context.user_data['main_message_id'] = message.message_id

# 시작 명령어 핸들러
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    # 기존 데이터 초기화
    context.user_data.clear()
    
    welcome_text = """
🚀 정보 입력 시스템에 오신 것을 환영합니다!

💡 안내사항:
본 서비스는 정확한 정보 제공을 위해 
전화번호 인증이 필수입니다.

아래 버튼을 눌러 전화번호를 공유해주세요.
"""
    
    keyboard = [[KeyboardButton("📱 전화번호 공유", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    return PHONE_AUTH

# 전화번호 인증 처리
async def handle_phone_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    if update.message.contact:
        phone_number = update.message.contact.phone_number
        context.user_data['phone_number'] = phone_number
        context.user_data['username'] = update.effective_user.username or update.effective_user.first_name
        context.user_data['user_id'] = update.effective_user.id
        
        # 연락처 메시지 삭제
        try:
            await update.message.delete()
        except:
            pass
        
        # 인증 완료 메시지와 함께 은행명 입력 시작
        welcome_text = f"""
✅ 전화번호 인증이 완료되었습니다!
전화번호: {phone_number}

{get_progress_bar(1)}

이제 은행명을 입력해주세요.
예: 국민은행, 신한은행, 우리은행 등
"""
        
        # 메인 메시지 생성 (이제부터 이 메시지만 계속 업데이트됨)
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data['main_message_id'] = message.message_id
        
        return BANK_NAME
    else:
        # 전화번호 공유가 아닌 다른 메시지가 온 경우
        try:
            await update.message.delete()
        except:
            pass
        
        return PHONE_AUTH

# 은행명 입력 처리
async def handle_bank_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    bank_name = update.message.text.strip()
    
    # 사용자가 보낸 메시지 삭제
    try:
        await update.message.delete()
    except:
        pass
    
    context.user_data['bank_name'] = bank_name
    
    # 수정 모드인지 확인
    if context.user_data.get('editing_mode'):
        context.user_data['editing_mode'] = False
        # 바로 확인 화면으로
        return await show_confirm_screen(context, chat_id)
    
    updated_text = f"""
✅ 은행명이 저장되었습니다: {bank_name}

{get_progress_bar(2)}

이제 계좌번호를 입력해주세요.
형식: 숫자와 하이픈(-)만 입력 가능 (예: 123-456-789012)
"""
    
    await update_message(context, chat_id, updated_text)
    return ACCOUNT_NUMBER

# 계좌번호 입력 처리
async def handle_account_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    account_number = update.message.text.strip()
    
    # 사용자가 보낸 메시지 삭제
    try:
        await update.message.delete()
    except:
        pass
    
    # 계좌번호 검증
    if not validate_account_number(account_number):
        error_text = f"""
{get_progress_bar(2)}

❌ 잘못된 계좌번호 형식입니다.

계좌번호는 다음과 같은 형식이어야 합니다:
- 숫자와 하이픈(-)만 포함
- 최소 10자 이상
- 예: 123-456-789012

다시 입력해주세요:
"""
        
        await update_message(context, chat_id, error_text)
        return ACCOUNT_NUMBER
    
    context.user_data['account_number'] = account_number
    
    # 수정 모드인지 확인
    if context.user_data.get('editing_mode'):
        context.user_data['editing_mode'] = False
        # 바로 확인 화면으로
        return await show_confirm_screen(context, chat_id)
    
    # 금액 선택 버튼 표시
    updated_text = f"""
✅ 계좌번호가 저장되었습니다: {account_number}

{get_progress_bar(3)}

이제 금액을 선택하거나 직접 입력해주세요:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("💵 10,000원", callback_data="amount_10000"),
            InlineKeyboardButton("💵 30,000원", callback_data="amount_30000")
        ],
        [
            InlineKeyboardButton("💵 50,000원", callback_data="amount_50000"),
            InlineKeyboardButton("💵 100,000원", callback_data="amount_100000")
        ],
        [
            InlineKeyboardButton("✏️ 직접 입력", callback_data="amount_custom")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_message(context, chat_id, updated_text, reply_markup)
    return AMOUNT

# 금액 선택 콜백 처리
async def handle_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    callback_data = query.data
    
    if callback_data == "amount_custom":
        # 직접 입력 모드
        custom_text = f"""
✅ 계좌번호: {context.user_data.get('account_number', '없음')}

{get_progress_bar(3)}

💰 금액을 직접 입력해주세요.
예: 1000000 또는 1,000,000

입력 후 전송해주세요:
"""
        
        await update_message(context, chat_id, custom_text)
        return AMOUNT_CUSTOM
    
    else:
        # 버튼으로 금액 선택
        amount_map = {
            "amount_10000": "10,000원",
            "amount_30000": "30,000원",
            "amount_50000": "50,000원",
            "amount_100000": "100,000원"
        }
        
        selected_amount = amount_map.get(callback_data, "알 수 없음")
        context.user_data['amount'] = selected_amount
        
        # 수정 모드인지 확인
        if context.user_data.get('editing_mode'):
            context.user_data['editing_mode'] = False
            # 바로 확인 화면으로
            return await show_confirm_screen(context, chat_id)
        
        updated_text = f"""
✅ 금액이 저장되었습니다: {selected_amount}

{get_progress_bar(4)}

관리자에게 전달할 메시지를 입력해주세요:
"""
        
        await update_message(context, chat_id, updated_text)
        return MESSAGE_INPUT

# 금액 직접 입력 처리
async def handle_amount_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    amount = update.message.text.strip()
    
    # 사용자가 보낸 메시지 삭제
    try:
        await update.message.delete()
    except:
        pass
    
    # 금액 검증
    try:
        clean_amount = amount.replace(',', '').replace(' ', '').replace('원', '')
        float(clean_amount)
        # 원 단위 추가
        if not amount.endswith('원'):
            amount = amount + '원'
        context.user_data['amount'] = amount
    except ValueError:
        error_text = f"""
{get_progress_bar(3)}

❌ 잘못된 금액 형식입니다.

금액은 다음과 같은 형식이어야 합니다:
- 숫자만 또는 쉼표 포함
- 예: 1000000 또는 1,000,000

다시 입력해주세요:
"""
        
        await update_message(context, chat_id, error_text)
        return AMOUNT_CUSTOM
    
    # 수정 모드인지 확인
    if context.user_data.get('editing_mode'):
        context.user_data['editing_mode'] = False
        # 바로 확인 화면으로
        return await show_confirm_screen(context, chat_id)
    
    updated_text = f"""
✅ 금액이 저장되었습니다: {amount}

{get_progress_bar(4)}

관리자에게 전달할 메시지를 입력해주세요:
"""
    
    await update_message(context, chat_id, updated_text)
    return MESSAGE_INPUT

# 관리자에게 전달할 메시지 입력 처리
async def handle_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message = update.message.text.strip()
    
    # 사용자가 보낸 메시지 삭제
    try:
        await update.message.delete()
    except:
        pass
    
    context.user_data['admin_message'] = message
    
    # 수정 모드인지 확인
    if context.user_data.get('editing_mode'):
        context.user_data['editing_mode'] = False
        # 바로 확인 화면으로
        return await show_confirm_screen(context, chat_id)
    
    # 입력된 정보 미리보기
    return await show_confirm_screen(context, chat_id)

# 확인 화면 표시 함수
async def show_confirm_screen(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    preview_text = f"""
📝 입력하신 정보를 확인해주세요:

{get_progress_bar(5)} ✅ 입력 완료

🏦 은행명: {context.user_data.get('bank_name', '없음')}
💳 계좌번호: {context.user_data.get('account_number', '없음')}
💰 금액: {context.user_data.get('amount', '없음')}
💬 관리자 메시지: {context.user_data.get('admin_message', '없음')}

아래 버튼을 눌러 최종 전송 여부를 선택해주세요:
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ 전송하기", callback_data="confirm_send"),
         InlineKeyboardButton("👁️ 상세보기", callback_data="view_form")],
        [InlineKeyboardButton("✏️ 수정하기", callback_data="edit_form"),
         InlineKeyboardButton("❌ 취소하기", callback_data="cancel_send")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_message(context, chat_id, preview_text, reply_markup)
    return CONFIRM_SEND

# 수정 메뉴 표시
async def edit_form_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    
    edit_text = f"""
✏️ 수정할 항목을 선택해주세요:

{get_progress_bar(5)}

현재 입력된 정보:
🏦 은행명: {context.user_data.get('bank_name', '없음')}
💳 계좌번호: {context.user_data.get('account_number', '없음')}
💰 금액: {context.user_data.get('amount', '없음')}
💬 관리자 메시지: {context.user_data.get('admin_message', '없음')}
"""
    
    keyboard = [
        [InlineKeyboardButton("🏦 은행명 수정", callback_data="edit_bank_name"),
         InlineKeyboardButton("💳 계좌번호 수정", callback_data="edit_account_number")],
        [InlineKeyboardButton("💰 금액 수정", callback_data="edit_amount"),
         InlineKeyboardButton("💬 메시지 수정", callback_data="edit_message")],
        [InlineKeyboardButton("◀️ 뒤로 가기", callback_data="back_to_confirm")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_message(context, chat_id, edit_text, reply_markup)
    return CONFIRM_SEND

# 수정 항목 선택 처리
async def edit_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    callback_data = query.data
    
    # 수정 모드 활성화
    context.user_data['editing_mode'] = True
    
    if callback_data == "edit_bank_name":
        edit_text = f"""
✏️ 은행명 수정

{get_progress_bar(5)}

현재 은행명: {context.user_data.get('bank_name', '없음')}

새로운 은행명을 입력해주세요:
예: 국민은행, 신한은행, 우리은행 등
"""
        await update_message(context, chat_id, edit_text)
        return BANK_NAME
    
    elif callback_data == "edit_account_number":
        edit_text = f"""
✏️ 계좌번호 수정

{get_progress_bar(5)}

현재 계좌번호: {context.user_data.get('account_number', '없음')}

새로운 계좌번호를 입력해주세요:
형식: 숫자와 하이픈(-)만 입력 가능 (예: 123-456-789012)
"""
        await update_message(context, chat_id, edit_text)
        return ACCOUNT_NUMBER
    
    elif callback_data == "edit_amount":
        edit_text = f"""
✏️ 금액 수정

{get_progress_bar(5)}

현재 금액: {context.user_data.get('amount', '없음')}

새로운 금액을 선택하거나 직접 입력해주세요:
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💵 10,000원", callback_data="amount_10000"),
                InlineKeyboardButton("💵 30,000원", callback_data="amount_30000")
            ],
            [
                InlineKeyboardButton("💵 50,000원", callback_data="amount_50000"),
                InlineKeyboardButton("💵 100,000원", callback_data="amount_100000")
            ],
            [
                InlineKeyboardButton("✏️ 직접 입력", callback_data="amount_custom")
            ],
            [
                InlineKeyboardButton("◀️ 뒤로 가기", callback_data="back_to_confirm")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update_message(context, chat_id, edit_text, reply_markup)
        return AMOUNT
    
    elif callback_data == "edit_message":
        edit_text = f"""
✏️ 관리자 메시지 수정

{get_progress_bar(5)}

현재 메시지: {context.user_data.get('admin_message', '없음')}

새로운 메시지를 입력해주세요:
"""
        await update_message(context, chat_id, edit_text)
        return MESSAGE_INPUT
    
    elif callback_data == "back_to_confirm":
        # 수정 모드 비활성화
        context.user_data['editing_mode'] = False
        # 확인 화면으로 돌아가기
        return await show_confirm_screen(context, chat_id)

# 입력 내용 확인 처리
async def view_form_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    
    form_text = f"""
📝 입력하신 정보 상세보기:

{get_progress_bar(5)} ✅ 입력 완료

👤 사용자: @{context.user_data.get('username', 'Unknown')} (ID: {context.user_data.get('user_id', 'Unknown')})
📱 전화번호: {context.user_data.get('phone_number', '없음')}
🏦 은행명: {context.user_data.get('bank_name', '없음')}
💳 계좌번호: {context.user_data.get('account_number', '없음')}
💰 금액: {context.user_data.get('amount', '없음')}
💬 관리자 메시지: {context.user_data.get('admin_message', '없음')}

등록 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ 전송하기", callback_data="confirm_send"),
         InlineKeyboardButton("✏️ 수정하기", callback_data="edit_form")],
        [InlineKeyboardButton("❌ 취소하기", callback_data="cancel_send")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_message(context, chat_id, form_text, reply_markup)

# 최종 전송 확인 처리
async def confirm_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    callback_data = query.data
    
    if callback_data == "confirm_send":
        summary = f"""
📝 새로운 정보가 도착했습니다!

👤 사용자: @{context.user_data.get('username', 'Unknown')} (ID: {context.user_data.get('user_id', 'Unknown')})
📱 전화번호: {context.user_data.get('phone_number', '없음')}
🏦 은행명: {context.user_data.get('bank_name', '없음')}
💳 계좌번호: {context.user_data.get('account_number', '없음')}
💰 금액: {context.user_data.get('amount', '없음')}
💬 관리자 메시지: {context.user_data.get('admin_message', '없음')}

등록 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 관리자 봇으로 정보 전송
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": ADMIN_BOT_CHAT_ID,
                        "text": summary
                    }
                )
            
            success_text = f"""
{get_progress_bar(5)} ✅ 완료

✅ 정보가 성공적으로 전송되었습니다!

감사합니다. 좋은 하루 되세요! 😊
"""
            
            if response.status_code == 200:
                await update_message(context, chat_id, success_text)
            else:
                await update_message(context, chat_id, "⚠️ 정보 전송 중 오류가 발생했습니다. 관리자에게 문의해주세요.")
                
        except Exception as e:
            logger.error(f"관리자 봇 전송 오류: {e}")
            await update_message(context, chat_id, "⚠️ 정보 전송 중 오류가 발생했습니다. 관리자에게 문의해주세요.")
    
    elif callback_data == "cancel_send":
        cancel_text = """
❌ 전송이 취소되었습니다.

/start 명령어를 입력하여 처음부터 다시 시작할 수 있습니다.
"""
        await update_message(context, chat_id, cancel_text)
    
    return ConversationHandler.END

# 계좌번호 검증 함수
def validate_account_number(account_number):
    """계좌번호 형식 검증 (숫자, 하이픈, 공백 허용)"""
    pattern = r'^[\d\- ]{10,30}$'
    return bool(re.match(pattern, account_number.strip()))

# 대화 취소
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    cancel_text = """
❌ 대화가 취소되었습니다.

/start 명령어로 다시 시작할 수 있습니다.
"""
    
    await update_message(context, chat_id, cancel_text)
    return ConversationHandler.END

def main():
    USER_BOT_TOKEN = "8553587759:AAH3CKXLMz3-kdjA7v-N9TGjP8E42Eog3Zk"
    
    application = Application.builder().token(USER_BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start)
        ],
        states={
            PHONE_AUTH: [
                MessageHandler(filters.CONTACT, handle_phone_auth),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_auth)
            ],
            BANK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bank_name)],
            ACCOUNT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_account_number)],
            AMOUNT: [
                CallbackQueryHandler(handle_amount_callback, pattern="^amount_"),
                CallbackQueryHandler(edit_item_callback, pattern="^(edit_amount|back_to_confirm)$")
            ],
            AMOUNT_CUSTOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount_custom)],
            MESSAGE_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message_input)],
            CONFIRM_SEND: [
                CallbackQueryHandler(edit_form_callback, pattern="^edit_form$"),
                CallbackQueryHandler(edit_item_callback, pattern="^edit_"),
                CallbackQueryHandler(edit_item_callback, pattern="^back_to_confirm$")
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False
    )
    
    application.add_handler(CallbackQueryHandler(view_form_callback, pattern="^view_form$"))
    application.add_handler(CallbackQueryHandler(confirm_send_callback, pattern="^(confirm_send|cancel_send)$"))
    application.add_handler(conv_handler)
    
    print("사용자 봇이 시작되었습니다...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()