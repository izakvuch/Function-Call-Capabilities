import base64
import logging
import threading
import random
from Socket import Socket
from AudioIO import AudioIO

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

class Realtime:
    def __init__(self, api_key, ws_url):
        self.socket = Socket(api_key, ws_url, on_msg=self.handle_message)
        self.audio_io = AudioIO(on_audio_callback=self.send_audio_to_socket)
        self.audio_thread = None  # Store thread references
        self.recv_thread = None

    def start(self):
        """ Start WebSocket and audio processing. """
        self.socket.connect()

        # Send initial request to start the conversation
        self.socket.send({
            'type': 'response.create',
            'response': {
                'modalities': ['audio', 'text'],
                'instructions': 'Please assist the user.'
            }
        })

        # Start processing microphone audio
        self.audio_thread = threading.Thread(target=self.audio_io.process_mic_audio)
        self.audio_thread.start()

        # Start audio streams (mic and speaker)
        self.audio_io.start_streams()

    def send_audio_to_socket(self, mic_chunk):
        """ Callback function to send audio data to the socket. """
        logging.info(f'🎤 Sending {len(mic_chunk)} bytes of audio data to socket.')
        encoded_chunk = base64.b64encode(mic_chunk).decode('utf-8')
        self.socket.send({'type': 'input_audio_buffer.append', 'audio': encoded_chunk})

    def handle_message(self, message):
        """ Handle incoming WebSocket messages. """
        event_type = message.get('type')
        logging.info(f'Received message type: {event_type}')

        if event_type == 'response.audio.delta':
            audio_content = base64.b64decode(message['delta'])
            self.audio_io.receive_audio(audio_content)
            logging.info(f'Received {len(audio_content)} bytes of audio data.')

        elif event_type == 'response.audio.done':
            logging.info('AI finished speaking.')

        elif event_type == 'function_call':
            # handles function call
            function_name = message['name']
            params = message['parameters']

            # example function calls
            if function_name == 'view_prescriptions':
                self.view_prescription(params['user_id'])

            elif function_name == 'schedule_appointments':
                self.schedule_appointments(params['user_id'], params['datetime'], params['reason'],params['doctor'])

            elif function_name == 'nearest_hospital':
                self.nearest_hospital(params['user_id'])

            elif function_name == 'view upcoming appointments':
                self.view_upcoming_app(params['user_id'])

            elif function_name == 'cancel appointment':
                self.cancel_app(params['user_id'], params['datetime'], params['doctor'])

            elif function_name == 'relay message':
                self.relay_message(params['user_id'], params['doctor'], params['message'])

            else: 
                logging.error(f'Function {function_name} is not defined.')


    """THIS IS WHERE ALL THE METHODS FOR FUNCTION CALLS GO"""
    def view_prescription(self, user_id):
        
        logging.info(f'Checking prescription routine for {user_id}')
        prescriptions = ['adderall', 'insulin', 'naxprozen', 'amoxicillin']
        selected_prescription = random.choice(prescriptions)
        with open("prescription_log.txt", 'a') as file:
            file.write(f"{user_id}, {selected_prescription}\n")
        # Sending function_call_output after action
        self.socket.send({
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'function_call_output': 'Checking prescriptions!'
            }
        })

        # OPTIONAL: add model responses after a function executes (CAN CHANGE TONE HERE)
        self.socket.send({
            'type': 'response.create',
            'response': {
                'modalities': ['text'],
                'instructions': 'Tell the user their {selected_prescription} prescription is avaliable for pickup.'
            }
        })

    
    def schedule_appointments(self, user_id, datetime, reason, doctor):
        logging.info(f'Checking for available appointments for {datetime}')
        with open("appointments_log.txt", 'a') as file:
            file.write(f"{user_id}, {datetime}, {reason}, {doctor}\n")
  
        self.socket.send({
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'function_call_output': 'Successfully scheduled appointment'
            }
        })


        self.socket.send({
            'type': 'response.create',
            'response': {
                'modalities': ['text'],
                'instructions': f'Your appointment has been successfully scheduled for {datetime} with Dr. {doctor}. Thank you!'
            }
        })

    def nearest_hospital(self, user_id):
        logging.info(f'Searching for hospital nearest to your location')
        hospitals = ['Sharp Chula Vista Medical Center', 'Sharp Coronado Hospital', 'Sharp Grossmont Hospital', 'Sharp Memorial Hospital', 'Sharp Mesa Vista Hospital']
        selected_hospital = random.choice(hospitals)

        self.socket.send({
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'function_call_output': 'Successfully located hospital'
            }
        })

    def view_upcoming_app(self, user_id):
        logging.info(f'Searching for upcoming appointments for user: {user_id}')
    
        upcoming_appointments = []

        with open("appointments_log.txt", 'r') as file:
            for line in file:
                entry_user_id, datetime, reason, doctor = line.strip().split(', ')
                if entry_user_id == user_id:
                    upcoming_appointments.append({
                        'datetime': datetime,
                        'reason': reason,
                        'doctor': doctor
                    })

        if upcoming_appointments:
            logging.info(f'Found {len(upcoming_appointments)} upcoming appointments for user {user_id}.')
        else:
            logging.info(f'No upcoming appointments found for user {user_id}.')

        self.socket.send({
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'function_call_output': f'Found {len(upcoming_appointments)} upcoming appointments for you.'
            }
        })
        
        self.socket.send({
            'type': 'response.create',
            'response': {
                'modalities': ['text'],
                'instructions': f'Your have an appointment on {upcoming_appointments["datetime"]} with Dr. {upcoming_appointments["doctor"]} for {upcoming_appointments["reason"]}'
            }
        })

    def cancel_app(self, user_id, datetime, doctor):
        logging.info(f'Cancelling appointments for {user_id} on {datetime} with {doctor}')

        self.socket.send({
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'function_call_output': 'Successfully cancelled appointment'
            }
        })

        self.socket.send({
            'type': 'response.create',
            'response': {
                'modalities': ['text'],
                'instructions': f'Your appointment on {datetime} with Dr. {doctor} has been successfully cancelled'
            }
        })

    def relay_message(self, user_id, doctor, message):
        logging.info(f'Relaying message to {doctor}')
        with open("message_log.txt", 'a') as file:
            file.write(f"{user_id}, {doctor}, {message}\n")

        self.socket.send({
            'type': 'conversation.item.create',
            'item': {
                'type': 'function_call_output',
                'function_call_output': 'Successfully relayed message'
            }
        })

        self.socket.send({
            'type': 'response.create',
            'response': {
                'modalities': ['text'],
                'instructions': f'Your message to Dr. {doctor}. Has been sent. Thank you!'
            }
        })

    def stop(self):
        """ Stop all processes cleanly. """
        logging.info('Shutting down Realtime session.')

        # Signal threads to stop
        self.audio_io._stop_event.set()
        self.socket.kill()

        # Stop audio streams
        self.audio_io.stop_streams()

        # Join threads to ensure they exit cleanly
        if self.audio_thread:
            self.audio_thread.join()
            logging.info('Audio processing thread terminated.')
