import os
import io
import logging
import datetime
import argparse
import configparser

from playsound import playsound
from google.cloud import vision, texttospeech
from google.cloud.vision import types


global is_pi
if os.uname().sysname == 'raspberrypi':
    from picamera import PiCamera
    is_pi = True
else:
    from cv2 import *
    is_pi = False


logger = logging.getLogger("pivizion")
def init_logger(log_to_file=None):
    """
    Initialize logger.
    """
    logger.setLevel(logging.INFO)
    if log_to_file:
        logging.basicConfig(filename='pivizion.log')
    else:
        logging.basicConfig()
    logging.captureWarnings(True)


class PiVizion(object):
    def visualize(self):
        """
        Process for visualizing an image.
        - Captures image, analyzes image for labels and text,
        creates audio of image analysis, plays audio file.
        """
        currentDT = datetime.datetime.now().strftime('%a, %b %d, %Y - %I:%M:%S %p')
        logger.info("Visualize Action Triggered at {currentDT}")

        image_name = self.get_image()
        result = self.analyze_image(image_name)
        text = f"{result['labels'][0].description if result['labels'] else 'No labels'}\n{result['texts'][0].description if result['texts'] else 'No Text'}"
        logger.info(f"Generated Text:\n{text}")
        self.speak(text)


    def get_image(self):
        """
        Captures an image to a file, returns the image filename.
        Returns image file name.
        """
        image_name = "image.jpg"

        if is_pi:
            logger.info("Running on raspberrypi, using PiCamera.")
            camera = PiCamera()
            camera.resolution = (1024, 768)
            camera.start_preview()
            camera.capture(image_name)
        else:
            logger.info("Running on Non-pi system, using openCV.")
            cam = VideoCapture(0)
            s, img = cam.read()

            if s:
                # namedWindow("cam-test")
                # imshow("cam-test", img)
                # waitKey(0)
                # destroyWindow("cam-test")
                imwrite(image_name, img)

        logger.info(f"Image Captured and saved as {image_name}")
        return image_name


    def analyze_image(self, image_name=None):
        """
        Analyzes an image using google cloud api.
        Returns a dictionary with resolved labels and text for the image.
        """
        if image_name:
            client = vision.ImageAnnotatorClient()

            with io.open(image_name, 'rb') as image_file:
                content = image_file.read()

            image = types.Image(content=content)

            labels_response = client.label_detection(image=image)
            labels = labels_response.label_annotations

            text_response = client.text_detection(image=image)
            texts = text_response.text_annotations

            if labels:
                logger.info(f'Labels: {labels[0].description}')
            if texts:
                logger.info(f'Text: {texts[0].description}')

            return {'labels' : labels, 'texts' : texts}


    def speak(self, text=None):
        """
        Creates audio file using google text to speech of the given text.
        """
        audio_out_name = 'out.mp3'

        if text:
            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.types.SynthesisInput(text=text)

            voice = texttospeech.types.VoiceSelectionParams(
                language_code='en-US',
                ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

            audio_config = texttospeech.types.AudioConfig(
                audio_encoding=texttospeech.enums.AudioEncoding.MP3)

            response = client.synthesize_speech(synthesis_input, voice, audio_config)

            with open(audio_out_name, 'wb') as out:
                out.write(response.audio_content)
                logger.info(f"Audio written to {audio_out_name}")

            playsound(audio_out_name)


def parse_config(filename=None):
    """
    Parse and validate config settings from a file.
    """
    valid_voice_genders = ("FEMALE", "MALE", "NEUTRAL")
    valid_voice_langs = ("en-US", "en-UK")

    config = configparser.ConfigParser()
    if not filename:
        print('not filename')
        filename = "config.ini"
    config.read(filename)

    if 'pivizion' in config:
        print('pivizion config detected')
        settings = config['pivizion']
        parsed_settings = dict(
            text_recognition = settings.getboolean('text_recognition', fallback=True),
            label_recognition = settings.getboolean('label_recognition', fallback=True),
            voice_gender = settings.get('voice_gender', fallback='FEMALE').upper(),
            voice_lang = settings.get('voice_lang', fallback='en-US')
        )

        # validate settings
        if parsed_settings['voice_gender'] not in valid_voice_genders:
            logger.error(f"voice_gender = {parsed_settings['voice_gender']} in configuration not valid. Setting to {valid_voice_genders[0]}")
            parsed_settings['voice_gender'] = valid_voice_genders[0]

        if parsed_settings['voice_lang'] not in valid_voice_langs:
            logger.error(f"voice_lang = {parsed_settings['voice_lang']} in configuration not valid. Setting to {valid_voice_langs[0]}")
            parsed_settings['voice_lang'] = valid_voice_langs[0]

        logger.info(f"Added configuration settings from config file.\n{parsed_settings}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default=None, dest='config_path',
                        help='Path to config file.')
    parser.add_argument('--test', '-t', default=False, action='store_true',
                        dest='is_test', help='Specify test.')
    parser.add_argument('--log', '-l', default=False, action='store_true',
                        dest='log_to_file', help='Log to file.')
    args = parser.parse_args()

    init_logger(log_to_file=args.log_to_file)
    parse_config(filename=args.config_path)

    # TODO: add button press event to call visualize
    #test = PiVizion()
    #test.visualize()


if (__name__ == '__main__'):
    main()
