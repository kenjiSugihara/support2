"""
Welfamily ── パートナー関係の「心の伴走者」チャットアプリ

夫婦・パートナー関係に悩む方が、日々の悩みや心配事を投げかけると、
心理学・男女コミュニケーションの知見にもとづき、優しく共感し、
今日から実践できるワンポイントアドバイスを返す Streamlit + Gemini アプリ。

- 仕様: docs/開発仕様書.md（v1.0）
- 知識ベース: knowledge.py（参考テキストを構造化・要約したもの）
"""

import streamlit as st
import google.generativeai as genai

from knowledge import build_knowledge_block

# =============================================================================
# 定数
# =============================================================================
MODEL_NAME = "gemini-2.5-flash"

# API 例外時に表示する、キャラクターのトーンに合わせた温かいフォールバック文言
FALLBACK_MESSAGE = (
    "申し訳ありません、現在少しお返事の準備に時間がかかっています。"
    "少し時間をおいてから、もう一度お話しを聞かせてくださいね。"
)

# 最初の一歩を踏み出しやすくするための相談テーマ例（クリックで送信）
STARTER_PROMPTS = [
    "最近、パートナーとの会話がなくて不安です",
    "パートナーが急に冷たくなった気がします",
    "話し合おうとするといつも喧嘩になってしまいます",
    "言いたいことがうまく伝えられません",
]

# システムプロンプト（AI の人格・知識・応答ルールの正規定義）
SYSTEM_INSTRUCTION = f"""
あなたは心理学と男女コミュニケーションの専門家であり、「Welfamily」という
ブランド名で、夫婦・パートナー・家族関係に悩む方に優しく寄り添う「心の伴走者」です。

# あなたの役割
- ユーザーが日々の悩みや心配事を投げかけたとき、まず深く共感し、
  そのうえで今日から実践できる小さな「ワンポイントアドバイス」を温かく届けます。

# 必ず守る応答ルール
1. ユーザーの感情（不安・怒り・悲しみ・寂しさなど）を絶対に否定しない。
   まず深く受け止めて共感することを、いつでも最優先にする。
2. 問題解決や正論（事実の通信線）を急がず、相手の心を肯定する
   「心の通信線」を先に繋ぐ。正論を突きつけない。
3. 専門用語を多用せず、温かく優しいトーンで語りかける。
4. 長くなりすぎない構成にし、今日から少しだけ実践できる一歩を添える。
5. 相手を「妻／夫」「女性／男性」と決めつけず、中立に受け止める。
6. 自分の名前を名乗るときは必ず「Welfamily」とする。
7. あなたは医師・カウンセラーの代わりではない。診断や断定はしない。
   命や安全に関わる恐れ（DV・自傷・虐待など）を感じたら、共感したうえで、
   警察・配偶者暴力相談支援センター・専門機関など公的な相談先を優しく案内する。

# 応答の型（目安）
共感（気持ちを受け止める）→ 必要なら視点をひとつ添える → 今日からできる小さな一歩
→ 安心できる短い締めくくり。

# ベースとする知識（この知見は「引き出し」。断定せず、相手の状況に沿って柔らかく使う）
{build_knowledge_block()}
""".strip()


# =============================================================================
# ページ・UI 設定
# =============================================================================
st.set_page_config(
    page_title="Welfamily - 心の伴走者",
    page_icon="🍀",
    layout="centered",
)

st.title("Welfamily - パートナー関係の心の伴走者 🍀")
st.write(
    "夫婦関係やパートナーとの関係で悩んでいること、日々のちょっとした心配事から"
    "大きなお悩みまで、何でもお話しください。Welfamilyが優しく寄り添い、"
    "ワンポイントでアドバイスをお届けします。"
)


# =============================================================================
# APIキー取得（StreamlitのSecretsからのみ／画面入力はさせない）
# =============================================================================
def get_api_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.error("システムエラー: APIキーが設定されていません。管理者に連絡してください。")
        return None


api_key = get_api_key()


# =============================================================================
# Gemini モデルの初期化（セッション内でキャッシュ）
# =============================================================================
@st.cache_resource(show_spinner=False)
def load_model(key: str):
    genai.configure(api_key=key)
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
    )


# =============================================================================
# 会話履歴の初期化
# =============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []


def stream_reply(prompt: str):
    """ユーザー入力に対する AI 応答を生成し、ストリーミング表示して履歴に保存する。"""
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            model = load_model(api_key)
            # これまでの履歴（最新のユーザー入力を除く）を Gemini 形式へ変換
            history = [
                {
                    "role": "user" if m["role"] == "user" else "model",
                    "parts": [m["content"]],
                }
                for m in st.session_state.messages[:-1]
            ]
            chat = model.start_chat(history=history)
            response = chat.send_message(prompt, stream=True)

            full_response = ""
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )
        except Exception:
            # 生のスタックトレースは見せず、温かいフォールバックを表示
            placeholder.markdown(FALLBACK_MESSAGE)


# =============================================================================
# これまでの会話を描画
# =============================================================================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# =============================================================================
# 相談テーマ例（会話がまだ無いときだけ表示）
# =============================================================================
starter_choice = None
if not st.session_state.messages:
    st.caption("こんなことからでも、気軽にお話しください 👇")
    cols = st.columns(2)
    for i, text in enumerate(STARTER_PROMPTS):
        if cols[i % 2].button(text, use_container_width=True, key=f"starter_{i}"):
            starter_choice = text


# =============================================================================
# 入力の受付（チャット欄 または 相談テーマ例のクリック）
# =============================================================================
prompt = st.chat_input("今の気持ちや悩みを教えてください...") or starter_choice

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if api_key:
        stream_reply(prompt)
    else:
        with st.chat_message("assistant"):
            st.markdown(FALLBACK_MESSAGE)
