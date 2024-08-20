from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from voice import StreamingSpeechToSpeech

app = FastAPI()

# Serve static files from the "static" directory
app.mount("/static", StaticFiles(directory="static"), name="static")

converter = StreamingSpeechToSpeech()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            converter.load_reference_speaker('resources/thalia.wav')
            output_path = converter.process_texts([data])
            with open(output_path, "rb") as audio_file:
                audio_data = audio_file.read()
                await websocket.send_bytes(audio_data)
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)