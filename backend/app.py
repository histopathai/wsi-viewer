import os
from datetime import datetime
import json
from flask import Flask, jsonify, send_from_directory, render_template, make_response, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


BASE_DIR = "/home/cilem/Lfstorage/wsis/breast_prostate_lenf_wsis/"
SLIDES_DIR = os.path.join(BASE_DIR, 'slides')
ANNOTATIONS_FILE = 'annotations.json'

def scan_organ_folder(path):
    """
    Bir organ klasörü altında hastalık tiplerini ve 
    altındaki .dzi dosyalarının isimlerini alır ve 
    dosyaları 'files' key'i içinde listeler.
    """
    organ_dict = {}
    try:
        disease_dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
        for disease in disease_dirs:
            disease_path = os.path.join(path, disease)
            dzi_files = [f for f in os.listdir(disease_path) if f.endswith('.dzi') and os.path.isfile(os.path.join(disease_path, f))]
            file_names = [os.path.splitext(f)[0] for f in dzi_files]

            # Dosyalar files anahtarı altında
            organ_dict[disease] = {"files": file_names}
    except Exception as e:
        print(f"Error scanning organ folder '{path}': {e}")
    return organ_dict

@app.route('/api/tree')
def get_tree():
    """
    slides klasörü altındaki organ klasörlerini tarar,
    her organ altındaki hastalık tiplerini ve .dzi dosyalarını listeler.
    Dosyalar 'files' anahtarı altında tutulur.
    """
    tree = {}
    try:
        organs = [d for d in os.listdir(SLIDES_DIR) if os.path.isdir(os.path.join(SLIDES_DIR, d))]
        for organ in organs:
            organ_path = os.path.join(SLIDES_DIR, organ)
            tree[organ] = scan_organ_folder(organ_path)
    except Exception as e:
        print(f"Error scanning base slides folder: {e}")
    return jsonify(tree)

@app.route('/slides/<path:filename>')
def serve_slide(filename):
    # filename 'organ/disease/file.dzi' gibi gelir
    response = make_response(send_from_directory(SLIDES_DIR, filename))
    response.headers['Cache-Control'] = 'public, max-age=86400'  # 1 gün önbellekle
    return response

@app.route('/api/save-annotations', methods=['POST'])
def save_annotations():
    try:
        data = request.get_json()
        
        existing_data = {}
        if os.path.exists(ANNOTATIONS_FILE):
            with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        
        timestamp = datetime.now().isoformat()
        for slide_path, annotation in data.items():
            existing_data[slide_path] = annotation
            existing_data[slide_path]['server_saved_at'] = timestamp
        
        with open(ANNOTATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"status": "success", "message": "Annotations saved successfully"}), 200
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get-annotations', methods=['GET'])
def get_annotations():
    try:
        if os.path.exists(ANNOTATIONS_FILE):
            with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data), 200
        return jsonify({}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=4000)
