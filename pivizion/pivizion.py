import os
import logging
import datetime
import argparse
import configparser

from playsound import playsound
from google.cloud import vision, texttospeech
from google.cloud.vision import types

VALID_VOICE_GENDERS = {"FEMALE":texttospeech.enums.SsmlVoiceGender.FEMALE,
                        "MALE":texttospeech.enums.SsmlVoiceGender.MALE,
                        "NEUTRAL":texttospeech.enums.SsmlVoiceGender.NEUTRAL}
VALID_VOICE_LANGS = ("en-US", "en-UK")

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
    def __init__(self, configuration):
        self.config = configuration

    def visualize(self):
        """
        Process for visualizing an image.
        - Captures image, analyzes image for labels and text,
        creates audio of image analysis, plays audio file.
        """
        currentDT = datetime.datetime.now().strftime('%a, %b %d, %Y - %I:%M:%S %p')
        logger.info("Visualize Action Triggered at {currentDT}")

        image_name = self.get_image()

        if not self.config['is_test']:
            result = self.analyze_image(image_name)
            text = f"{result['labels'][0].description if result['labels'] else 'No labels'}\n{result['texts'][0].description if result['texts'] else 'No Text'}"
            logger.info(f"Generated Text:\n{text}")
            self.speak(text)
        else:
            logger.info('Test flag set, not analyzing image.')


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
            labels = texts = None

            with open(image_name, 'rb') as image_file:
                content = image_file.read()

            image = types.Image(content=content)

            if self.config['label_recognition']:
                labels_response = client.label_detection(image=image)
                labels = labels_response.label_annotations

            if self.config['text_recognition']:
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
                #language_code='en-US',
                language_code=self.config['voice_lang'],
                #ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)
                ssml_gender=self.config['voice_gender'])
            audio_config = texttospeech.types.AudioConfig(
                audio_encoding=texttospeech.enums.AudioEncoding.MP3)

            response = client.synthesize_speech(synthesis_input, voice, audio_config)

            with open(audio_out_name, 'wb') as out:
                out.write(response.audio_content)
                logger.info(f"Audio written to {audio_out_name}")

            playsound(audio_out_name)
            os.remove(audio_out_name)


def get_config(filename=None, is_test=False):
    """
    Get configuration settings.
    Return parsed and validated config from file or default.
    """

    # default config
    configuration = dict(
        text_recognition = True,
        label_recognition = True,
        voice_gender = VALID_VOICE_GENDERS['FEMALE'],
        voice_lang = VALID_VOICE_LANGS[0],
        is_test = False
    )

    # set default config path if not given
    if not filename:
        filename = "pivizion/config.ini"

    config = configparser.ConfigParser()
    config.read(filename)

    if 'pivizion' in config:
        settings = config['pivizion']

        # get settings from config file
        configuration['text_recognition'] = settings.getboolean('text_recognition', fallback=True)
        configuration['label_recognition'] = settings.getboolean('label_recognition', fallback=True)
        configuration['voice_gender'] = settings.get('voice_gender', fallback="FEMALE").upper()
        configuration['voice_lang'] = settings.get('voice_lang', fallback=VALID_VOICE_LANGS[0])
        configuration['is_test'] = settings.getboolean('is_test', fallback=False)

        # validate settings
        if configuration['voice_gender'] not in VALID_VOICE_GENDERS:
            logger.error(f"voice_gender = {configuration['voice_gender']} in configuration not valid. Setting to {VALID_VOICE_GENDERS[0]}")
            configuration['voice_gender'] = VALID_VOICE_GENDERS["FEMALE"]
        else:
            configuration['voice_gender'] = VALID_VOICE_GENDERS.get(configuration["voice_gender"])

        if configuration['voice_lang'] not in VALID_VOICE_LANGS:
            logger.error(f"voice_lang = {configuration['voice_lang']} in configuration not valid. Setting to {VALID_VOICE_LANGS[0]}")
            configuration['voice_lang'] = VALID_VOICE_LANGS[0]

        logger.info(f"Added configuration settings from config file {filename}.")
    else:
        logger.info(f"Using default config.")

    # override config if command line test arg is set.
    if is_test:
        configuration['is_test'] = True
        logger.info('is_test argument overwritten from command line.')

    logger.info(f"Configuration settings added.\n{configuration}")

    return configuration


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
    configuration = get_config(filename=args.config_path, is_test=args.is_test)

    # TODO: add button press event to call visualize
    pivizion = PiVizion(configuration)
    #pivizion.visualize()


if (__name__ == '__main__'):
    main()
