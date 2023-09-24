import json
import random
import os
import shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from extensions.api.util import build_parameters, try_start_cloudflared
from modules import shared
from modules.chat import generate_chat_reply
from modules.LoRA import add_lora_to_model
from modules.models import load_model, unload_model
from modules.models_settings import (
    update_model_parameters
)
from modules.text_generation import (
    encode,
    generate_reply,
    stop_everything_event
)
from modules.utils import get_available_models


def get_model_info():
    return {
        'model_name': shared.model_name,
        'lora_names': shared.lora_names,
        # dump
        'shared.settings': shared.settings,
        'shared.args': vars(shared.args),
    }
'''
def delete_unit(username, char_id):
    # Generate the JSON file path based on the provided username and char_id
    json_file_path = os.path.join('characters', username, f'{char_id}.json')

    # Check if the JSON file exists
    if os.path.exists(json_file_path):
        os.remove(json_file_path)  # Delete the JSON file
        # Use this:
        response_data = {'message': f'File {char_id}.json deleted successfully'}
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
    else:
        return jsonify({'error': f'File {char_id}.json not found'}), 404

# New /deleteAllUnits method
def delete_all_units(username):
    # Generate the directory path based on the provided username
    character_dir = os.path.join('characters', username)

    # Check if the directory exists
    if os.path.exists(character_dir):
        # Iterate through files in the directory and delete JSON files
        deleted_files = []
        for filename in os.listdir(character_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(character_dir, filename)
                os.remove(file_path)
                deleted_files.append(filename)

        if deleted_files:
            return jsonify({'message': f'{len(deleted_files)} files deleted successfully', 'deleted_files': deleted_files}), 200
        else:
            return jsonify({'message': 'No JSON files found in the directory'}), 200
    else:
        return jsonify({'error': 'Directory not found'}), 404

# New /delete_user_character_dir method
def delete_user_character_dir(username):
    # Generate the directory path based on the provided username
    character_dir = os.path.join('characters', username)

    # Check if the directory exists
    if os.path.exists(character_dir):
        # Use shutil.rmtree to remove the directory and its contents
        shutil.rmtree(character_dir)
        return jsonify({'message': f'Directory for {username} and its contents deleted successfully'}), 200
    else:
        return jsonify({'error': f'Directory for {username} not found'}), 404
'''        

class Handler(BaseHTTPRequestHandler):
 # New /delete_user_character_dir method
 
    def delete_user_character_dir(self, username):
        # Generate the directory path based on the provided username
        character_dir = os.path.join('characters', username)

        # Check if the directory exists
        if os.path.exists(character_dir):
            # Use shutil.rmtree to remove the directory and its contents
            shutil.rmtree(character_dir)
            response_data = {'message': f'Directory for {username} and its contents deleted successfully'}
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            response_data = {'error': f'Directory for {username} not found'}
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))           

    def delete_unit(self, username, char_id):
        # Generate the JSON file path based on the provided username and char_id
        json_file_path = os.path.join('/src/characters', username, char_id, f'{char_id}.json')

        # Delete the entire directory, including the JSON file, ignoring errors if it doesn't exist
        try:
            shutil.rmtree(os.path.join('/src/characters', username, char_id))
        except FileNotFoundError:
            pass

        # Delete the memories directory and its contents, ignoring errors if it doesn't exist
        try:
            shutil.rmtree(os.path.join('/src/extensions/long_term_memory/user_data/bot_memories', username, char_id))
        except FileNotFoundError:
            pass

        response_data = {'message': f'Directory {char_id} and its contents deleted successfully'}
        self.wfile.write(json.dumps(response_data).encode('utf-8'))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()




    # New /deleteAllUnits method
    def delete_all_units(self, username):
        # Generate the directory path based on the provided username
        character_dir = os.path.join('characters', username)

        # Check if the directory exists
        if os.path.exists(character_dir):
            # Iterate through files in the directory and delete JSON files
            deleted_files = []
            for filename in os.listdir(character_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(character_dir, filename)
                    os.remove(file_path)
                    deleted_files.append(filename)

            if deleted_files:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response_data = {'message': f'{len(deleted_files)} files deleted successfully', 'deleted_files': deleted_files}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response_data = {'message': 'No JSON files found in the directory'}
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
        else:
            self.send_error(404, 'Directory not found')
            
    def do_GET(self):
        if self.path == '/api/v1/model':
            self.send_response(200)
            self.end_headers()
            response = json.dumps({
                'result': shared.model_name
            })

            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_error(404)


    # New /delete_user_character_dir method    
    
            
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = json.loads(self.rfile.read(content_length).decode('utf-8'))

        if self.path == '/api/v1/generate':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            prompt = body['prompt']
            generate_params = build_parameters(body)
            stopping_strings = generate_params.pop('stopping_strings')
            generate_params['stream'] = False

            generator = generate_reply(
                prompt, generate_params, stopping_strings=stopping_strings, is_chat=False)

            answer = ''
            for a in generator:
                answer = a

            response = json.dumps({
                'results': [{
                    'text': answer
                }]
            })

            self.wfile.write(response.encode('utf-8'))


        elif self.path == '/api/v1/chat':
       
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            user_input = body['user_input']
            char_id = body['character']
            username = body['username']
            regenerate = body.get('regenerate', False)
            _continue = body.get('_continue', False)
            
            json_file_path = os.path.join('/src/characters', username, char_id, f'{char_id}.json')
            if not os.path.exists(json_file_path):
                self.send_error(500, 'Character.json does not exist! CreateUnit first!')
                return               
                
            generate_params = build_parameters(body, chat=True)
            generate_params['stream'] = False
         
            # Check if the JSON file exists
      
            generator = generate_chat_reply(
                user_input, generate_params, regenerate=regenerate, _continue=_continue, loading_message=False)

            answer = generate_params['history']
            for a in generator:
                answer = a

            response = json.dumps({
                'results': [{
                    'history': answer
                }]
            })

            self.wfile.write(response.encode('utf-8'))
            
        elif self.path == '/api/deleteUnit':
            if 'username' not in body or 'char_id' not in body:
                self.send_error(400, 'Missing username or char_id in request body')
                return

            username = body['username']
            char_id = body['char_id']
            # /deleteUnit endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.delete_unit(username, char_id)

        elif self.path == '/api/deleteAllUnits':
            if 'username' not in body:
                self.send_error(400, 'Missing username in request body')
                return

            username = body['username']
            # /deleteAllUnits endpoint
            self.delete_all_units(username)

        elif self.path == '/api/deleteUserCharacterDir':
            if 'username' not in body:
                self.send_error(400, 'Missing username in request body')
                return

            username = body['username']
            # /delete_user_character_dir endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.delete_user_character_dir(username)
            
        elif self.path == '/api/createUnit':
            self.send_response(201)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            data = body

            if 'username' not in data or 'ai_id' not in data:
                self.send_error(400, 'Missing required fields in the request body')
            else:
                username = data['username']
                ai_id = data['ai_id']

                # Use ai_id as the directory name
                character_dir = os.path.join('/src/characters', username, ai_id)

                # Create the directory
                os.makedirs(character_dir, exist_ok=True)

                # Use ai_id as the filename
                json_file_path = os.path.join(character_dir, f'{ai_id}.json')
                with open(json_file_path, 'w') as json_file:
                    json_data = {'char_name': data.get('char_name', ''), 'convo_id': ai_id}
                    json_file.write(json.dumps(json_data, indent=4))

                response_data = {
                    'message': 'File created successfully',
                    'convo_id': ai_id
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))


                
        elif self.path == '/api/v1/stop-stream':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            stop_everything_event()

            response = json.dumps({
                'results': 'success'
            })

            self.wfile.write(response.encode('utf-8'))

        elif self.path == '/api/v1/model':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            # by default return the same as the GET interface
            result = shared.model_name

            # Actions: info, load, list, unload
            action = body.get('action', '')

            if action == 'load':
                model_name = body['model_name']
                args = body.get('args', {})
                print('args', args)
                for k in args:
                    setattr(shared.args, k, args[k])

                shared.model_name = model_name
                unload_model()

                model_settings = get_model_settings_from_yamls(shared.model_name)
                shared.settings.update(model_settings)
                update_model_parameters(model_settings, initial=True)

                if shared.settings['mode'] != 'instruct':
                    shared.settings['instruction_template'] = None

                try:
                    shared.model, shared.tokenizer = load_model(shared.model_name)
                    if shared.args.lora:
                        add_lora_to_model(shared.args.lora)  # list

                except Exception as e:
                    response = json.dumps({'error': {'message': repr(e)}})

                    self.wfile.write(response.encode('utf-8'))
                    raise e

                shared.args.model = shared.model_name

                result = get_model_info()

            elif action == 'unload':
                unload_model()
                shared.model_name = None
                shared.args.model = None
                result = get_model_info()

            elif action == 'list':
                result = get_available_models()

            elif action == 'info':
                result = get_model_info()

            response = json.dumps({
                'result': result,
            })

            self.wfile.write(response.encode('utf-8'))

        elif self.path == '/api/v1/token-count':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            tokens = encode(body['prompt'])[0]
            response = json.dumps({
                'results': [{
                    'tokens': len(tokens)
                }]
            })

            self.wfile.write(response.encode('utf-8'))
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()


def _run_server(port: int, share: bool = False, tunnel_id=str):
    address = '0.0.0.0' if shared.args.listen else '127.0.0.1'

    server = ThreadingHTTPServer((address, port), Handler)

    def on_start(public_url: str):
        print(f'Starting non-streaming server at public url {public_url}/api')

    if share:
        try:
            try_start_cloudflared(port, tunnel_id, max_attempts=3, on_start=on_start)
        except Exception:
            pass
    else:
        print(
            f'Starting API at http://{address}:{port}/api')

    server.serve_forever()


def start_server(port: int, share: bool = False, tunnel_id=str):
    Thread(target=_run_server, args=[port, share, tunnel_id], daemon=True).start()
