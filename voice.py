import os
import torch
from openvoice import se_extractor
from openvoice.api import ToneColorConverter
from melo.api import TTS
import time

class StreamingSpeechToSpeech:
    def __init__(self, ckpt_converter='checkpoints_v2/converter', output_dir='outputs_v2'):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=self.device)
        self.tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')

        self.tts_models = {}
        self.speaker_ses = {}
        # self.load_tts_model('EN_NEWEST')
        # speaker_ids = self.tts_models['EN_NEWEST'].hps.data.spk2id
        self.load_tts_model('EN_NEWEST')
        self.load_speaker_se('EN-Newest')

    def load_reference_speaker(self, reference_speaker):
        self.target_se, _ = se_extractor.get_se(reference_speaker, self.tone_color_converter, vad=True)

    def load_tts_model(self, language):
        if language not in self.tts_models:
            self.tts_models[language] = TTS(language=language, device=self.device)

    def load_speaker_se(self, speaker_key):
        if speaker_key not in self.speaker_ses:
            speaker_key_formatted = speaker_key.lower().replace('_', '-')
            self.speaker_ses[speaker_key] = torch.load(f'checkpoints_v2/base_speakers/ses/{speaker_key_formatted}.pth', map_location=self.device)

    @torch.inference_mode()
    def convert_speech(self, text, language, speaker_key, speed=1.0):

        model = self.tts_models[language]
        speaker_id = model.hps.data.spk2id['EN-Newest']
        source_se = self.speaker_ses['EN-Newest']

        src_path = f'{self.output_dir}/tmp_{speaker_key}.wav'
        save_path = f'{self.output_dir}/output_v2_{speaker_key}.wav'

        tts_start = time.time()
        model.tts_to_file(text, speaker_id, src_path, speed=speed)
        tts_end = time.time()

        convert_start = time.time()
        encode_message = "@MyShell"
        self.tone_color_converter.convert(
            audio_src_path=src_path,
            src_se=source_se,
            tgt_se=self.target_se,
            output_path=save_path,
            message=encode_message
        )
        convert_end = time.time()

        print(f"Time for TTS: {tts_end - tts_start:.2f} seconds")
        print(f"Time for Tone Color Conversion: {convert_end - convert_start:.2f} seconds")

        return save_path

    def process_texts(self, texts):

        for text in texts:

            
            
            start_time = time.time()

            self.convert_speech(text, 'EN_NEWEST', 'EN_NEWEST')
            end_time = time.time()
            print(f"Total processing time: {end_time - start_time:.2f} seconds")

       

# Usage
if __name__ == "__main__":
    converter = StreamingSpeechToSpeech()
    converter.load_reference_speaker('resources/thalia.wav')
    converter.process_texts(["warmup"])
    texts = [
           "Hello, how are you doing today?",
        "I'm doing great, thanks for asking!",
        "THIRTY YEARS AGO, if you'd asked someone to name the most important writers in America, Cormac McCarthy would not have been one of them. His masterpiece, Blood Meridian, had drifted out of print. In fact, all of his books had. McCarthy had lived most of his adult life in near-poverty, shunning publicity, turning down teaching and speaking engagements, and—one suspects—guessing his books would not sell much."

    ]

        
    converter.process_texts(texts)