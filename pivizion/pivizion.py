import os
import io
import logging
import datetime

from playsound import playsound
from google.cloud import vision, texttospeech
from google.cloud.vision import types


global is_pi
if os.uname().sysname == 'raspberrypi':
    import picamera
    is_pi = True
else:
    from cv2 import *
    is_pi = False


logger = logging.getLogger(__name__)
def init_logger():
    """
    Initialize logger.
    """
    logger.setLevel(logging.INFO)
    logging.basicConfig(filename='pivizion.log')
    logging.captureWarnings(True)


class PiVizion(object):
    def visualize(self):
        """
        Process for visualizing an image.
        - Captures image, analyzes image for labels and text,
        creates audio of image analysis, plays audio file.
        """
        init_logger()
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
            print("Pi cam")
        else:
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


def main():
    # TODO: add button press event to call visualize
    test = PiVizion()
    test.visualize()


if (__name__ == '__main__'):
    main()
