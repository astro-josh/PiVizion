import os
import io


from playsound import playsound
from google.cloud import vision, texttospeech
from google.cloud.vision import types

global is_pi

print(os.uname().sysname)
if os.uname().sysname == 'raspberrypi':
    import picamera
    is_pi = True
else:
    from cv2 import *
    is_pi = False


class PiVizion(object):

    def visualize(self):
        """
        Process for visualizing an image.
        - Captures image, analyzes image for labels and text,
        creates audio of image analysis, plays audio file.
        """
        image_name = self.get_image()
        result = self.analyze_image(image_name)
        text = f"{result['labels'][0].description if result['labels'] else 'No labels'}\n{result['texts'][0].description if result['texts'] else 'No Text'}"
        print(text)
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
                print('image written')

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
                print(f'Labels: {labels[0].description}')
            if texts:
                print(f'Text: {texts[0].description}')

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
                print("Audio written to file.")

            playsound(audio_out_name)




test = PiVizion()
test.visualize()
