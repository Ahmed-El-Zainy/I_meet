import os
import uuid
import requests
import gradio as gr

API_BASE = os.environ.get("API_BASE_URL", "http://api:8000")

CLIENT_TOKENS = {
    "Client A": os.environ.get("CLIENT_A_TOKEN", ""),
    "Client B": os.environ.get("CLIENT_B_TOKEN", ""),
}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def chat_fn(message: str, history: list, client_choice: str, conversation_id: str):
    token = CLIENT_TOKENS.get(client_choice, "")
    if not token:
        return history + [[message, "⚠️ No token configured for this client."]], conversation_id

    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    try:
        resp = requests.post(
            f"{API_BASE}/chat/query",
            json={"message": message, "conversation_id": conversation_id},
            headers=_headers(token),
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("response", "")
        citations = data.get("citations", [])
        if citations:
            answer += "\n\n**Sources:** " + " | ".join(citations)
    except requests.HTTPError as e:
        answer = f"⚠️ API error {e.response.status_code}: {e.response.text}"
    except Exception as e:
        answer = f"⚠️ Error: {e}"

    history = history + [[message, answer]]
    return history, conversation_id


def clear_fn(client_choice: str, conversation_id: str):
    token = CLIENT_TOKENS.get(client_choice, "")
    if token and conversation_id:
        try:
            requests.delete(
                f"{API_BASE}/chat/{conversation_id}",
                headers=_headers(token),
                timeout=10,
            )
        except Exception:
            pass
    return [], ""


with gr.Blocks(title="AI Meeting Intelligence") as demo:
    gr.Markdown("# 🎙️ AI Meeting Intelligence — RAG Chatbot")

    with gr.Row():
        client_selector = gr.Dropdown(
            choices=["Client A", "Client B"],
            value="Client A",
            label="Select Client",
        )
        conv_id_state = gr.State("")

    chatbot = gr.Chatbot(label="Conversation", height=500)
    msg_box = gr.Textbox(placeholder="Ask about your meetings...", label="Message", lines=2)

    with gr.Row():
        send_btn = gr.Button("Send", variant="primary")
        clear_btn = gr.Button("Clear conversation")

    send_btn.click(
        chat_fn,
        inputs=[msg_box, chatbot, client_selector, conv_id_state],
        outputs=[chatbot, conv_id_state],
    ).then(lambda: "", outputs=msg_box)

    msg_box.submit(
        chat_fn,
        inputs=[msg_box, chatbot, client_selector, conv_id_state],
        outputs=[chatbot, conv_id_state],
    ).then(lambda: "", outputs=msg_box)

    clear_btn.click(
        clear_fn,
        inputs=[client_selector, conv_id_state],
        outputs=[chatbot, conv_id_state],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
