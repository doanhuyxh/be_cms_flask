from flask import Flask, request, jsonify, send_from_directory
from flask_pymongo import PyMongo
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Cấu hình kết nối MongoDB
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/project_cms_web"
mongo = PyMongo(app)

# Cấu hình thư mục upload
UPLOAD_FOLDER = './uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['STATIC_FOLDER'] = UPLOAD_FOLDER

project_build_collection = mongo.db.project_build
project_collection = mongo.db.project
project_file_collection = mongo.db.project_file


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"error": "No files part"}), 400

    files = request.files.getlist('files')  # Lấy danh sách file
    if not files or all(file.filename == '' for file in files):
        return jsonify({"error": "No selected files"}), 400

    uploaded_files = []
    for file in files:
        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(filepath)
            except IOError:
                return jsonify({"error": "File save failed"}), 500

            project_file_collection.insert_one({"filename": filename, "filepath": filepath})

            path = "http://127.0.0.1:8080"+"/" +"uploads"+"/"+filename
            uploaded_files.append(path)

    return jsonify(uploaded_files), 200

@app.route('/assets', methods=['GET'])
def get_assets():
    """
    Trả về danh sách các assets từ MongoDB.
    """
    try:
        assets = list(project_file_collection.find({}, {"_id": 0, "filename": 1, "filepath": 1}))
        asset_list = [{"src": f"http://127.0.0.1:8080/uploads/{asset['filename']}"} for asset in assets]
        return jsonify(asset_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_assets', methods=['DELETE'])
def delete_assets():
    """
    Xóa các assets được chỉ định.
    """
    try:
        data = request.get_json()
        if not data or 'assets' not in data:
            return jsonify({"error": "Invalid request data"}), 400

        asset_urls = data['assets']
        for asset_url in asset_urls:
            filename = asset_url.split("/")[-1]
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Xóa file khỏi hệ thống
            if os.path.exists(filepath):
                os.remove(filepath)

            # Xóa asset khỏi MongoDB
            project_file_collection.delete_one({"filename": filename})

        return jsonify({"message": "Assets deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/save_project', methods=['POST'])
def save_project():
    """
    Lưu dữ liệu dự án vào MongoDB.
    """
    try:
        data = request.get_json()
        if not data or 'project' not in data:
            return jsonify({"error": "Invalid request data"}), 400

        project = data['project']
        project_id = project.get('id', None)

        if not project_id:
            return jsonify({"error": "Project ID is required"}), 400

        existing_project = project_collection.find_one({"id": project_id})
        if existing_project:
            project_collection.update_one({"id": project_id}, {"$set": project})
        else:
            project_collection.insert_one(project)

        return jsonify({"message": "Project saved successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/load_project/<project_id>', methods=['GET'])
def load_project(project_id):
    """
    Tải dữ liệu dự án từ MongoDB.
    """
    try:
        project = project_collection.find_one({"id": project_id}, {"_id": 0})
        if not project:
            return jsonify({"error": "Project not found"}), 404

        return jsonify({"project": project}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/public/<project_id>', methods=['POST'])
def public_project(project_id):
    """
    Cập nhật trạng thái public của dự án.
    """
    try:
        data = request.get_json()
        html = data['html']
        css = data['css']
        print(html)
        check = project_build_collection.find_one({"project_id": project_id})
        if check:
            project_build_collection.update_one({"project_id": project_id}, {"$set": {"html": html, "css": css}})
        else:
            project_build_collection.insert_one({"project_id": project_id, "html": html, "css": css})

        return jsonify({"message": "Project published successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_public/<project_id>', methods=['GET'])
def get_public_project(project_id):
    """
    Lấy dự án public từ MongoDB.
    """
    try:
        project = project_build_collection.find_one({"project_id": project_id})
        if not project:
            return jsonify({"error": "Project not found"}), 404

        return jsonify({"project": project}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)