import os
import json
import random
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw
import base64
import io
import math

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

class PalmTreeDetector:
    """Dummy palm tree detector for demonstration"""
    
    def __init__(self):
        self.detection_count = 0
    
    def detect_trees_in_bounds(self, bounds, image_size=(1000, 1000)):
        """
        Generate dummy palm tree detections within the given bounds
        In a real implementation, this would process actual satellite imagery
        """
        south_west = bounds['_southWest']
        north_east = bounds['_northEast']
        
        # Calculate area size
        lat_range = north_east['lat'] - south_west['lat']
        lng_range = north_east['lng'] - south_west['lng']
        
        # Generate random number of trees (between 50-200 for demo)
        num_trees = random.randint(50, 200)
        
        trees = []
        for i in range(num_trees):
            # Generate random coordinates within bounds
            lat = south_west['lat'] + random.random() * lat_range
            lng = south_west['lng'] + random.random() * lng_range
            
            # Add some randomness to make it look more natural
            tree_size = random.uniform(0.5, 2.0)  # Tree size factor
            confidence = random.uniform(0.7, 0.95)  # Detection confidence
            
            trees.append({
                'id': i + 1,
                'lat': lat,
                'lng': lng,
                'size': tree_size,
                'confidence': confidence
            })
        
        self.detection_count += num_trees
        return trees
    
    def create_visualization(self, bounds, trees, image_size=(800, 600)):
        """Create a visualization of detected trees"""
        # Create a simple image representation
        img = Image.new('RGB', image_size, color=(210, 235, 210))  # Light green background
        draw = ImageDraw.Draw(img)
        
        # Draw bounds outline
        margin = 50
        draw.rectangle([margin, margin, image_size[0]-margin, image_size[1]-margin], 
                      outline=(0, 100, 0), width=3)
        
        # Draw trees as circles
        for tree in trees:
            # Convert lat/lng to image coordinates (simplified)
            lat_norm = (tree['lat'] - bounds['_southWest']['lat']) / (bounds['_northEast']['lat'] - bounds['_southWest']['lat'])
            lng_norm = (tree['lng'] - bounds['_southWest']['lng']) / (bounds['_northEast']['lng'] - bounds['_southWest']['lng'])
            
            x = margin + lng_norm * (image_size[0] - 2*margin)
            y = margin + lat_norm * (image_size[1] - 2*margin)
            
            # Size based on tree size
            radius = max(2, int(tree['size'] * 3))
            
            # Color based on confidence
            green_intensity = int(tree['confidence'] * 255)
            color = (0, green_intensity, 0)
            
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                        fill=color, outline=(0, 80, 0))
        
        # Add title
        draw.text((20, 20), f"Detected Palm Trees: {len(trees)}", fill=(0, 0, 0))
        
        # Convert to base64 for frontend display
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"

def create_mission_plan(trees, bounds):
    """Create mission plan in the required format"""
    
    mission_items = []
    for i, tree in enumerate(trees):
        mission_items.append({
            "type": "SimpleItem",
            "command": 16,  # MAV_CMD_NAV_WAYPOINT
            "frame": 3,     # MAV_FRAME_GLOBAL_RELATIVE_ALT
            "params": [0, 0, 0, 0, tree['lat'], tree['lng'], 50],  # lat, lng, alt(50m)
            "autoContinue": True
        })
    
    plan = {
        "fileType": "Plan",
        "geoFence": {
            "circles": [],
            "polygons": [],
            "version": 2
        },
        "groundStation": "QGroundControl",
        "mission": {
            "cruiseSpeed": 15,
            "firmwareType": 12,
            "hoverSpeed": 5,
            "items": mission_items,
            "plannedHomePosition": [
                bounds['_southWest']['lat'],
                bounds['_southWest']['lng'],
                0
            ],
            "vehicleType": 2,
            "version": 2
        },
        "rallyPoints": {
            "points": [],
            "version": 2
        },
        "version": 1
    }
    
    return plan

# Initialize detector
detector = PalmTreeDetector()

@app.route('/')
def hello():
    return jsonify({
        "message": "Palm Tree Detection Backend is running!",
        "endpoints": {
            "process_region": "POST /process_region",
            "health": "GET /health"
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "detections_made": detector.detection_count})

@app.route('/process_region', methods=['POST'])
def process_region():
    """
    Process selected region and detect palm trees
    Expected JSON: {"bounds": {"_southWest": {"lat": x, "lng": y}, "_northEast": {"lat": x, "lng": y}}}
    """
    try:
        data = request.get_json()
        
        if not data or 'bounds' not in data:
            return jsonify({"error": "No bounds provided"}), 400
        
        bounds = data['bounds']
        
        # Validate bounds
        required_keys = ['_southWest', '_northEast']
        for key in required_keys:
            if key not in bounds:
                return jsonify({"error": f"Missing {key} in bounds"}), 400
            if 'lat' not in bounds[key] or 'lng' not in bounds[key]:
                return jsonify({"error": f"Missing lat/lng in {key}"}), 400
        
        # Calculate area (simplified)
        lat_diff = bounds['_northEast']['lat'] - bounds['_southWest']['lat']
        lng_diff = bounds['_northEast']['lng'] - bounds['_southWest']['lng']
        area_hectares = abs(lat_diff * lng_diff * 10000)  # Rough approximation
        
        # Detect trees
        trees = detector.detect_trees_in_bounds(bounds)
        
        # Create visualization
        visualization = detector.create_visualization(bounds, trees)
        
        # Create mission plan
        mission_plan = create_mission_plan(trees, bounds)
        
        return jsonify({
            "message": f"Berhasil mendeteksi {len(trees)} pohon sawit dalam area {area_hectares:.2f} hektar",
            "statistics": {
                "trees_detected": len(trees),
                "area_hectares": area_hectares,
                "tree_density": len(trees) / area_hectares if area_hectares > 0 else 0
            },
            "visualization": visualization,
            "plan": mission_plan
        })
        
    except Exception as e:
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

if __name__ == '__main__':
    print("Starting Palm Tree Detection Backend...")
    print("Endpoints:")
    print("  GET  /health - Check server status")
    print("  POST /process_region - Process selected area")
    app.run(debug=True, host='0.0.0.0', port=5000)