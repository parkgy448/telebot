# admin_bot.py - 개선된 관리자 봇
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 관리자 봇 토큰
ADMIN_BOT_TOKEN = "8064894285:AAEcMp1PDiNvUBClv9VQPimyibrTzLXZVRY"

# 관리자 Chat ID 저장소 (실제로는 데이터베이스 사용 권장)
ADMIN_CHAT_IDS = set()

# 수신된 메시지 저장소 (실제로는 데이터베이스 사용 권장)
received_messages = []

# 시작 명령어 핸들러
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Chat ID 자동 저장
    ADMIN_CHAT_IDS.add(chat_id)
    logger.info(f"관리자 Chat ID 저장: {chat_id} (@{username})")
    
    welcome_message = f"""
👑 관리자 봇에 오신 것을 환영합니다!

✅ Chat ID가 자동으로 등록되었습니다.
📱 Chat ID: `{chat_id}`
👤 관리자: @{username}

━━━━━━━━━━━━━━━━━━
📋 이 봇의 기능:
━━━━━━━━━━━━━━━━━━

🔔 사용자로부터 전송된 정보를 실시간으로 수신
📊 수신된 정보 목록 조회 및 통계
📈 상세 분석 및 보고서

━━━━━━━━━━━━━━━━━━
🎯 사용 가능한 명령어:
━━━━━━━━━━━━━━━━━━

/start - 봇 시작 및 Chat ID 등록
/help - 도움말 보기
/status - 현재 상태 확인
/list - 수신된 메시지 목록 (최근 10개)
/stats - 통계 정보 확인
/clear - 메시지 기록 초기화

현재 대기 중입니다... 📡
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

# 도움말 명령어 핸들러
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📖 관리자 봇 도움말

━━━━━━━━━━━━━━━━━━
📋 명령어 설명:
━━━━━━━━━━━━━━━━━━

/start
└─ 봇을 시작하고 Chat ID를 등록합니다

/help
└─ 이 도움말 메시지를 표시합니다

/status
└─ 현재 봇 상태 및 수신 통계를 확인합니다

/list
└─ 최근 수신된 메시지 목록을 표시합니다
   (최근 10개 항목)

/stats
└─ 자세한 통계 정보를 확인합니다
   • 총 수신 건수
   • 은행별 통계
   • 금액별 통계
   • 시간대별 통계

/clear
└─ 저장된 메시지 기록을 초기화합니다
   ⚠️ 이 작업은 되돌릴 수 없습니다

━━━━━━━━━━━━━━━━━━
📡 수신되는 정보:
━━━━━━━━━━━━━━━━━━

• 사용자 정보 (닉네임, ID, 전화번호)
• 은행명
• 계좌번호
• 금액
• 관리자 메시지
• 등록 시간

━━━━━━━━━━━━━━━━━━
💡 팁:
━━━━━━━━━━━━━━━━━━

• 새로운 정보가 도착하면 실시간으로 알림을 받습니다
• /list 명령어로 언제든지 과거 내역을 확인할 수 있습니다
• 데이터는 봇이 재시작되면 초기화됩니다
  (영구 저장을 원하시면 개발자에게 문의하세요)

문의사항이 있으시면 개발자에게 연락해주세요.
"""
    
    await update.message.reply_text(help_text)

# 상태 확인 명령어 핸들러
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_messages = len(received_messages)
    registered_admins = len(ADMIN_CHAT_IDS)
    
    # 최근 메시지 시간
    if received_messages:
        last_message_time = received_messages[-1].get('timestamp', 'N/A')
        last_user = received_messages[-1].get('username', 'Unknown')
    else:
        last_message_time = "없음"
        last_user = "없음"
    
    status_message = f"""
📊 관리자 봇 상태

━━━━━━━━━━━━━━━━━━
🟢 시스템 상태
━━━━━━━━━━━━━━━━━━

🤖 봇 상태: 정상 작동 중
📡 수신 모드: 활성화
👥 등록된 관리자: {registered_admins}명
📝 총 수신 건수: {total_messages}건

━━━━━━━━━━━━━━━━━━
📅 최근 활동
━━━━━━━━━━━━━━━━━━

⏰ 마지막 수신: {last_message_time}
👤 마지막 사용자: @{last_user}

━━━━━━━━━━━━━━━━━━
💡 빠른 액세스
━━━━━━━━━━━━━━━━━━

• 메시지 목록: /list
• 상세 통계: /stats
• 도움말: /help

시스템이 정상적으로 작동 중입니다. ✅
"""
    
    await update.message.reply_text(status_message)

# 메시지 목록 조회 명령어 핸들러
async def list_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not received_messages:
        await update.message.reply_text(
            "📭 아직 수신된 메시지가 없습니다.\n\n"
            "사용자가 정보를 전송하면 여기에 표시됩니다."
        )
        return
    
    # 최근 10개 메시지만 표시
    recent_messages = received_messages[-10:]
    
    message_text = f"""
📋 수신된 메시지 목록
(최근 {len(recent_messages)}개 / 총 {len(received_messages)}개)

━━━━━━━━━━━━━━━━━━
"""
    
    for idx, msg in enumerate(reversed(recent_messages), 1):
        message_text += f"""
📌 메시지 #{len(received_messages) - idx + 1}
━━━━━━━━━━━━━━━━━━
👤 사용자: @{msg.get('username', 'Unknown')} (ID: {msg.get('user_id', 'N/A')})
📱 전화번호: {msg.get('phone_number', '없음')}
🏦 은행: {msg.get('bank_name', '없음')}
💳 계좌: {msg.get('account_number', '없음')}
💰 금액: {msg.get('amount', '없음')}
💬 메시지: {msg.get('admin_message', '없음')}
⏰ 시간: {msg.get('timestamp', 'N/A')}

"""
    
    # 메시지가 너무 길면 분할 전송
    if len(message_text) > 4000:
        parts = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(message_text)

# 통계 정보 명령어 핸들러
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not received_messages:
        await update.message.reply_text(
            "📊 통계를 생성할 데이터가 없습니다.\n\n"
            "사용자가 정보를 전송하면 통계가 생성됩니다."
        )
        return
    
    # 통계 계산
    total_count = len(received_messages)
    
    # 은행별 통계
    bank_stats = {}
    for msg in received_messages:
        bank = msg.get('bank_name', '알 수 없음')
        bank_stats[bank] = bank_stats.get(bank, 0) + 1
    
    # 금액별 통계 (정확한 금액)
    amounts = [msg.get('amount', '0').replace(',', '').replace('원', '').strip() for msg in received_messages]
    
    # 사용자별 통계
    user_stats = {}
    for msg in received_messages:
        user = msg.get('username', 'Unknown')
        user_stats[user] = user_stats.get(user, 0) + 1
    
    stats_text = f"""
📊 상세 통계 정보

━━━━━━━━━━━━━━━━━━
📈 전체 현황
━━━━━━━━━━━━━━━━━━

📝 총 수신 건수: {total_count}건
👥 등록된 관리자: {len(ADMIN_CHAT_IDS)}명
⏰ 첫 수신 시간: {received_messages[0].get('timestamp', 'N/A')}
⏰ 최근 수신 시간: {received_messages[-1].get('timestamp', 'N/A')}

━━━━━━━━━━━━━━━━━━
🏦 은행별 통계
━━━━━━━━━━━━━━━━━━

"""
    
    for bank, count in sorted(bank_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_count) * 100
        stats_text += f"• {bank}: {count}건 ({percentage:.1f}%)\n"
    
    stats_text += f"""
━━━━━━━━━━━━━━━━━━
👥 사용자별 통계
━━━━━━━━━━━━━━━━━━

"""
    
    for user, count in sorted(user_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
        stats_text += f"• @{user}: {count}건\n"
    
    stats_text += """
━━━━━━━━━━━━━━━━━━
💡 팁
━━━━━━━━━━━━━━━━━━

• /list - 최근 메시지 목록 보기
• /clear - 통계 초기화하기
"""
    
    await update.message.reply_text(stats_text)

# 메시지 기록 초기화 명령어 핸들러
async def clear_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("✅ 예, 삭제합니다", callback_data="confirm_clear"),
            InlineKeyboardButton("❌ 아니오", callback_data="cancel_clear")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    confirm_text = f"""
⚠️ 경고: 메시지 기록 초기화

현재 {len(received_messages)}개의 메시지가 저장되어 있습니다.

정말로 모든 메시지 기록을 삭제하시겠습니까?
이 작업은 되돌릴 수 없습니다.
"""
    
    await update.message.reply_text(confirm_text, reply_markup=reply_markup)

# 초기화 확인 콜백 핸들러
async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_clear":
        count = len(received_messages)
        received_messages.clear()
        
        await query.edit_message_text(
            f"✅ 총 {count}개의 메시지 기록이 삭제되었습니다.\n\n"
            "새로운 메시지부터 다시 기록됩니다."
        )
    else:
        await query.edit_message_text(
            "❌ 삭제가 취소되었습니다.\n\n"
            "메시지 기록이 유지됩니다."
        )

# 사용자 봇으로부터의 메시지 수신 핸들러
async def receive_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """사용자 봇으로부터 전송된 데이터를 수신하고 저장"""
    message_text = update.message.text
    
    # 메시지가 정보 형식인지 확인 (간단한 파싱)
    if "📝 새로운 정보가 도착했습니다!" in message_text:
        # 메시지 저장
        message_data = {
            'raw_message': message_text,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'message_id': update.message.message_id
        }
        
        # 간단한 파싱 (실제로는 정규표현식 사용 권장)
        lines = message_text.split('\n')
        for line in lines:
            if '사용자:' in line:
                message_data['username'] = line.split('@')[1].split('(')[0].strip() if '@' in line else 'Unknown'
                if 'ID:' in line:
                    message_data['user_id'] = line.split('ID:')[1].split(')')[0].strip()
            elif '전화번호:' in line:
                message_data['phone_number'] = line.split('전화번호:')[1].strip()
            elif '은행명:' in line:
                message_data['bank_name'] = line.split('은행명:')[1].strip()
            elif '계좌번호:' in line:
                message_data['account_number'] = line.split('계좌번호:')[1].strip()
            elif '💰 금액:' in line:
                message_data['amount'] = line.split('금액:')[1].strip()
            elif '관리자 메시지:' in line:
                message_data['admin_message'] = line.split('관리자 메시지:')[1].strip()
        
        received_messages.append(message_data)
        logger.info(f"새로운 메시지 수신: {message_data.get('username', 'Unknown')}")
        
        # 수신 확인 응답 (선택사항)
        keyboard = [
            [
                InlineKeyboardButton("📋 전체 목록 보기", callback_data="show_list"),
                InlineKeyboardButton("📊 통계 보기", callback_data="show_stats")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ 메시지 수신 완료 (총 {len(received_messages)}건)\n\n"
            "빠른 액세스:",
            reply_markup=reply_markup
        )

# 빠른 액세스 콜백 핸들러
async def quick_access_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_list":
        # /list 명령어와 동일한 동작
        await list_messages_inline(query)
    elif query.data == "show_stats":
        # /stats 명령어와 동일한 동작
        await stats_inline(query)

async def list_messages_inline(query):
    """인라인 버튼으로 호출되는 메시지 목록"""
    if not received_messages:
        await query.edit_message_text(
            "📭 아직 수신된 메시지가 없습니다."
        )
        return
    
    recent_messages = received_messages[-5:]
    
    message_text = f"📋 최근 메시지 ({len(recent_messages)}개)\n\n"
    
    for idx, msg in enumerate(reversed(recent_messages), 1):
        message_text += f"""
📌 메시지 #{len(received_messages) - idx + 1}
👤 @{msg.get('username', 'Unknown')}
🏦 {msg.get('bank_name', '없음')} | 💰 {msg.get('amount', '없음')}
⏰ {msg.get('timestamp', 'N/A')}
━━━━━━━━━━━━━━━━━━
"""
    
    await query.edit_message_text(message_text)

async def stats_inline(query):
    """인라인 버튼으로 호출되는 통계"""
    if not received_messages:
        await query.edit_message_text(
            "📊 통계를 생성할 데이터가 없습니다."
        )
        return
    
    total_count = len(received_messages)
    bank_stats = {}
    for msg in received_messages:
        bank = msg.get('bank_name', '알 수 없음')
        bank_stats[bank] = bank_stats.get(bank, 0) + 1
    
    stats_text = f"""
📊 간단 통계

총 수신: {total_count}건

🏦 은행별:
"""
    
    for bank, count in sorted(bank_stats.items(), key=lambda x: x[1], reverse=True):
        stats_text += f"• {bank}: {count}건\n"
    
    await query.edit_message_text(stats_text)

# 일반 메시지 처리 (echo)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """일반 텍스트 메시지 처리"""
    # 사용자 봇의 메시지인지 확인
    if "📝 새로운 정보가 도착했습니다!" in update.message.text:
        await receive_user_data(update, context)
    else:
        # 일반 메시지는 간단히 확인만
        await update.message.reply_text(
            f"✉️ 메시지 수신: {update.message.text[:50]}...\n\n"
            "명령어를 사용하려면 /help를 입력하세요."
        )

def main():
    """메인 함수"""
    # 애플리케이션 생성
    application = Application.builder().token(ADMIN_BOT_TOKEN).build()
    
    # 명령어 핸들러 추가
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("list", list_messages))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("clear", clear_messages))
    
    # 콜백 쿼리 핸들러 추가
    application.add_handler(CallbackQueryHandler(clear_callback, pattern="^(confirm_clear|cancel_clear)$"))
    application.add_handler(CallbackQueryHandler(quick_access_callback, pattern="^(show_list|show_stats)$"))
    
    # 메시지 핸들러 추가
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # 봇 시작
    print("=" * 50)
    print("👑 관리자 봇이 시작되었습니다!")
    print("=" * 50)
    print(f"📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🤖 봇 토큰: {ADMIN_BOT_TOKEN[:20]}...")
    print(f"📡 수신 대기 중...")
    print("=" * 50)
    print("\n💡 팁: Telegram에서 /start 명령어로 봇을 활성화하세요\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()