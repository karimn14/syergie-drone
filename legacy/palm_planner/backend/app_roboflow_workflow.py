import os
import json
import random
import numpy as np
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import base64
import io
import math
import logging
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration - Use environment variables for security
ROBOFLOW_CONFIG = {
    "API_KEY": os.getenv("ROBOFLOW_API_KEY", "Pocq0zfIpMM4NSTIESk2"),
    "WORKSPACE": "palmset",
    "WORKFLOW_ID": "detect-count-and-visualize-5"
}

# Try to import the detectors with improved error handling
detector_modules = {}

try:
    from palm_tree_detector import PalmTreeDetector
    detector_modules['palm_tree'] = True
    logger.info("✅ PalmTreeDetector imported successfully")
except ImportError as e:
    detector_modules['palm_tree'] = False
    logger.warning(f"❌ PalmTreeDetector import failed: {e}")

try:
    from roboflow_integration import RoboflowPalmDetector
    detector_modules['roboflow_integration'] = True
    logger.info("✅ RoboflowPalmDetector imported successfully")
except ImportError as e:
    detector_modules['roboflow_integration'] = False
    logger.warning(f"❌ RoboflowPalmDetector import failed: {e}")

try:
    from roboflow_workflow import RoboflowWorkflowDetector
    detector_modules['roboflow_workflow'] = True
    logger.info("✅ RoboflowWorkflowDetector imported successfully")
except ImportError as e:
    detector_modules['roboflow_workflow'] = False
    logger.warning(f"❌ RoboflowWorkflowDetector import failed: {e}")

# Initialize detectors
detectors = {}
current_detector = None
detector_health = {}

def initialize_detectors():
    """Initialize all available detectors with comprehensive error handling"""
    global detectors, current_detector, detector_health
    
    detectors = {}
    detector_health = {}
    
    try:
        # 0. Priority: Custom YOLO Model (your best.pt)
        custom_model_path = "models/best.pt"
        if os.path.exists(custom_model_path) and detector_modules.get('palm_tree', False):
            try:
                detectors['local_custom'] = PalmTreeDetector(model_path=custom_model_path, confidence_threshold=0.5)
                detector_health['local_custom'] = 'healthy'
                current_detector = 'local_custom'
                logger.info(f"✅ Custom YOLO model loaded from {custom_model_path}")
                
                # Test the custom model
                test_bounds = {
                    '_southWest': {'lat': -6.853, 'lng': 107.314},
                    '_northEast': {'lat': -6.850, 'lng': 107.318}
                }
                try:
                    test_trees, test_image = detectors['local_custom'].detect_trees(test_bounds)
                    logger.info(f"✅ Custom YOLO model test successful - Detected {len(test_trees)} trees")
                    detector_health['local_custom'] = 'tested'
                except Exception as test_e:
                    logger.warning(f"⚠️ Custom YOLO model test had issues: {test_e}")
                    detector_health['local_custom'] = 'unstable'
                    
            except Exception as e:
                logger.error(f"❌ Failed to load custom YOLO model: {e}")
                detector_health['local_custom'] = 'failed'

        # 1. Priority: Roboflow Workflow with inference-sdk
        api_key = ROBOFLOW_CONFIG["API_KEY"]
        
        if (api_key and api_key != "YOUR_VALID_API_KEY_HERE" and 
            detector_modules.get('roboflow_workflow', False)):
            try:
                detectors['roboflow_workflow'] = RoboflowWorkflowDetector(
                    api_key=api_key,
                    workspace_name=ROBOFLOW_CONFIG["WORKSPACE"],
                    workflow_id=ROBOFLOW_CONFIG["WORKFLOW_ID"]
                )
                detector_health['roboflow_workflow'] = 'healthy'
                # Only set as current if custom model is not available
                if current_detector is None:
                    current_detector = 'roboflow_workflow'
                logger.info("✅ Roboflow Workflow (inference-sdk) initialized")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize Roboflow Workflow: {e}")
                detector_health['roboflow_workflow'] = 'failed'
        
        # 2. Fallback: Local Roboflow model
        if detector_modules.get('roboflow_integration', False):
            try:
                detectors['roboflow_local'] = RoboflowPalmDetector()
                detector_health['roboflow_local'] = 'healthy'
                if current_detector is None:
                    current_detector = 'roboflow_local'
                logger.info("✅ Local Roboflow detector initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize local Roboflow detector: {e}")
                detector_health['roboflow_local'] = 'failed'
        
        # 3. Fallback: Basic palm tree detector
        if detector_modules.get('palm_tree', False) and current_detector is None:
            try:
                detectors['local'] = PalmTreeDetector()
                detector_health['local'] = 'healthy'
                current_detector = 'local'
                logger.info("✅ Local palm tree detector initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize local detector: {e}")
                detector_health['local'] = 'failed'
        
        # If no detectors available, we'll use dummy mode
        if not detectors:
            logger.warning("⚠️ No detectors available - using dummy mode")
            current_detector = 'dummy'
            detector_health['dummy'] = 'healthy'
            
        logger.info(f"📡 Available detectors: {list(detectors.keys())}")
        logger.info(f"🎯 Current detector: {current_detector}")
            
    except Exception as e:
        logger.error(f"❌ Critical error initializing detectors: {e}")
        traceback.print_exc()
        current_detector = 'dummy'

def create_waypoints_file(trees, bounds):
    """Create waypoints file in QGC WPL 110 format with loiter time"""
    try:
        lines = []
        
        # Header QGC WPL
        lines.append("QGC WPL 110")
        
        # Home position (first waypoint)
        if trees and _is_valid_coordinate(trees[0]['lat'], trees[0]['lng']):
            home_lat = trees[0]['lat']
            home_lng = trees[0]['lng']
        else:
            home_lat = (bounds['_southWest']['lat'] + bounds['_northEast']['lat']) / 2
            home_lng = (bounds['_southWest']['lng'] + bounds['_northEast']['lng']) / 2
        
        # Ensure home position is valid
        if not _is_valid_coordinate(home_lat, home_lng):
            home_lat = -6.9025
            home_lng = 107.6186
        
        # Home waypoint (index 0)
        # Format: INDEX CURRENT_WP COORD_FRAME COMMAND PARAM1 PARAM2 PARAM3 PARAM4 LAT LON ALT AUTOCONTINUE
        home_waypoint = f"0\t1\t0\t16\t0\t0\t0\t0\t{home_lat:.7f}\t{home_lng:.7f}\t10.000000\t1"
        lines.append(home_waypoint)
        
        # Mission waypoints for each tree
        for i, tree in enumerate(trees):
            if not _is_valid_coordinate(tree['lat'], tree['lng']):
                continue
                
            # Waypoint to tree location
            waypoint = f"{i+1}\t0\t3\t16\t0.000000\t0.000000\t0.000000\t0.000000\t{tree['lat']:.7f}\t{tree['lng']:.7f}\t10.000000\t1"
            lines.append(waypoint)
            
            # Loiter waypoint (5 seconds) at tree location
            loiter_waypoint = f"{i+2}\t0\t3\t19\t5.000000\t0.000000\t0.000000\t0.000000\t{tree['lat']:.7f}\t{tree['lng']:.7f}\t10.000000\t1"
            lines.append(loiter_waypoint)
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error creating waypoints file: {e}")
        traceback.print_exc()
        return create_fallback_waypoints_file()

def create_fallback_waypoints_file():
    """Create fallback waypoints file"""
    return """QGC WPL 110
0	1	0	16	0	0	0	0	-6.9025000	107.6186000	10.000000	1
1	0	3	16	0.000000	0.000000	0.000000	0.000000	-6.9028000	107.6190000	10.000000	1
2	0	3	19	5.000000	0.000000	0.000000	0.000000	-6.9028000	107.6190000	10.000000	1
3	0	3	16	0.000000	0.000000	0.000000	0.000000	-6.9032000	107.6188000	10.000000	1
4	0	3	19	5.000000	0.000000	0.000000	0.000000	-6.9032000	107.6188000	10.000000	1"""
        
def create_mission_plan(trees, bounds):
    """Create mission plan in the required format with validation"""
    try:
        mission_items = []
        
        for i, tree in enumerate(trees):
            # Validate tree coordinates
            if not _is_valid_coordinate(tree['lat'], tree['lng']):
                logger.warning(f"Skipping tree with invalid coordinates: {tree}")
                continue
                
            mission_items.append({
                "type": "SimpleItem",
                "command": 16,  # MAV_CMD_NAV_WAYPOINT
                "frame": 3,     # MAV_FRAME_GLOBAL_RELATIVE_ALT
                "params": [0, 0, 0, None, tree['lat'], tree['lng'], 10.0],  # lat, lng, alt(10m)
                "autoContinue": True,
                "doJumpId": i + 1
            })
        
        # Validate home position - use first tree or center of bounds
        if trees and _is_valid_coordinate(trees[0]['lat'], trees[0]['lng']):
            home_lat = trees[0]['lat']
            home_lng = trees[0]['lng']
        else:
            home_lat = (bounds['_southWest']['lat'] + bounds['_northEast']['lat']) / 2
            home_lng = (bounds['_southWest']['lng'] + bounds['_northEast']['lng']) / 2
        
        # Ensure home position is valid
        if not _is_valid_coordinate(home_lat, home_lng):
            home_lat = -6.9025  # Default fallback
            home_lng = 107.6186
        
        plan = {
            "fileType": "Plan",
            "geoFence": {
                "circles": [],
                "polygons": [],
                "version": 2
            },
            "mission": {
                "cruiseSpeed": 5,
                "firmwareType": 12,
                "hoverSpeed": 3,
                "items": mission_items,
                "plannedHomePosition": [home_lat, home_lng, 10.0],
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
        
    except Exception as e:
        logger.error(f"Error creating mission plan: {e}")
        traceback.print_exc()
        # Return empty plan as fallback
        return {
            "fileType": "Plan",
            "geoFence": {"circles": [], "polygons": [], "version": 2},
            "mission": {
                "cruiseSpeed": 5,
                "firmwareType": 12,
                "hoverSpeed": 3,
                "items": [],
                "plannedHomePosition": [-6.9025, 107.6186, 10.0],
                "vehicleType": 2,
                "version": 2
            },
            "rallyPoints": {"points": [], "version": 2},
            "version": 1
        }

def _is_valid_coordinate(lat, lng):
    """Validate geographic coordinates"""
    try:
        return (-90 <= lat <= 90) and (-180 <= lng <= 180)
    except:
        return False

# Initialize detectors on startup
initialize_detectors()

@app.route('/')
def hello():
    available_models = list(detectors.keys())
    if not available_models:
        available_models = ['dummy']
    
    return jsonify({
        "message": "Palm Tree Detection Backend - Enhanced Version with Custom YOLO",
        "available_models": available_models,
        "current_model": current_detector,
        "model_health": detector_health,
        "custom_yolo_available": 'local_custom' in detectors,
        "roboflow_workflow_available": 'roboflow_workflow' in detectors,
        "api_key_configured": ROBOFLOW_CONFIG["API_KEY"] != "YOUR_VALID_API_KEY_HERE",
        "endpoints": {
            "process_region": "POST /process_region",
            "health": "GET /health",
            "model_info": "GET /model_info",
            "switch_model": "POST /switch_model",
            "update_api_key": "POST /update_api_key",
            "reinitialize": "POST /reinitialize"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "available_models": list(detectors.keys()),
        "current_model": current_detector,
        "model_health": detector_health,
        "detector_modules": detector_modules,
        "custom_yolo_loaded": 'local_custom' in detectors and detector_health.get('local_custom') in ['healthy', 'tested'],
        "api_key_configured": ROBOFLOW_CONFIG["API_KEY"] != "YOUR_VALID_API_KEY_HERE"
    })

@app.route('/model_info')
def model_info():
    if current_detector and current_detector in detectors and current_detector != 'dummy':
        detector = detectors[current_detector]
        if hasattr(detector, 'get_model_info'):
            try:
                info = detector.get_model_info()
                info['health'] = detector_health.get(current_detector, 'unknown')
                info['current_detector'] = current_detector
                
                # Add custom info for custom YOLO model
                if current_detector == 'local_custom':
                    info['model_path'] = 'models/best.pt'
                    info['model_type'] = 'Custom YOLO Model'
                    info['description'] = 'Your trained YOLO model for palm tree detection'
                
                return jsonify(info)
            except Exception as e:
                logger.error(f"Error getting model info: {e}")
                return jsonify({"error": f"Failed to get model info: {str(e)}"}), 500
        else:
            return jsonify({
                "model_type": "Local Model",
                "current_detector": current_detector,
                "health": detector_health.get(current_detector, 'unknown')
            })
    else:
        return jsonify({
            "error": "No active model",
            "current_mode": "dummy" if current_detector == 'dummy' else "unknown",
            "solution": "Configure API key or check model files"
        }), 500

@app.route('/switch_model', methods=['POST'])
def switch_model():
    """Switch between available models with validation"""
    global current_detector
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        model_name = data.get('model', '').lower()
        
        available_models = list(detectors.keys())
        if not available_models:
            available_models = ['dummy']
        
        if model_name in available_models:
            current_detector = model_name
            return jsonify({
                "message": f"Switched to {model_name} model",
                "current_model": current_detector,
                "health": detector_health.get(current_detector, 'unknown')
            })
        else:
            return jsonify({
                "error": f"Model '{model_name}' not available",
                "available_models": available_models
            }), 400
            
    except Exception as e:
        logger.error(f"Error switching model: {e}")
        return jsonify({"error": f"Failed to switch model: {str(e)}"}), 500

@app.route('/update_api_key', methods=['POST'])
def update_api_key():
    """Endpoint to update API key without restarting server"""
    global detectors, current_detector, detector_health
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
            
        new_api_key = data.get('api_key')
        
        if not new_api_key:
            return jsonify({"error": "No API key provided"}), 400
        
        # Update configuration
        ROBOFLOW_CONFIG["API_KEY"] = new_api_key
        
        # Try to initialize Roboflow Workflow with new key
        if detector_modules.get('roboflow_workflow', False):
            try:
                detectors['roboflow_workflow'] = RoboflowWorkflowDetector(
                    api_key=new_api_key,
                    workspace_name=ROBOFLOW_CONFIG["WORKSPACE"],
                    workflow_id=ROBOFLOW_CONFIG["WORKFLOW_ID"]
                )
                detector_health['roboflow_workflow'] = 'healthy'
                # Don't change current detector automatically - let user choose
                logger.info("✅ Roboflow Workflow reinitialized with new API key")
                
                return jsonify({
                    "message": "API key updated successfully",
                    "workflow_available": True,
                    "current_model": current_detector,  # Keep current model
                    "health": detector_health.get(current_detector, 'unknown')
                })
                
            except Exception as e:
                detectors.pop('roboflow_workflow', None)
                detector_health['roboflow_workflow'] = 'failed'
                
                return jsonify({
                    "error": f"Failed to initialize with new API key: {str(e)}",
                    "workflow_available": False,
                    "current_model": current_detector,
                    "health": detector_health.get(current_detector, 'unknown')
                }), 400
        else:
            return jsonify({
                "error": "roboflow_workflow module not available",
                "solution": "Check imports and dependencies"
            }), 400
            
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        return jsonify({"error": f"Failed to update API key: {str(e)}"}), 500

@app.route('/reinitialize', methods=['POST'])
def reinitialize():
    """Reinitialize all detectors"""
    try:
        initialize_detectors()
        return jsonify({
            "message": "Detectors reinitialized successfully",
            "available_models": list(detectors.keys()),
            "current_model": current_detector,
            "model_health": detector_health
        })
    except Exception as e:
        logger.error(f"Error reinitializing detectors: {e}")
        return jsonify({"error": f"Failed to reinitialize: {str(e)}"}), 500

@app.route('/process_region', methods=['POST'])
def process_region():
    """
    Process selected region with comprehensive error handling and fallbacks
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        if 'bounds' not in data:
            return jsonify({"error": "No bounds provided"}), 400
        
        bounds = data['bounds']
        
        # Validate bounds structure
        validation_result = validate_bounds(bounds)
        if not validation_result['valid']:
            return jsonify({
                "error": "Invalid bounds provided",
                "details": validation_result['errors']
            }), 400
        
        # Calculate area for statistics
        area_info = calculate_area_info(bounds)
        
        # Try to use current detector if available
        detection_result = None
        
        if current_detector and current_detector in detectors and current_detector != 'dummy':
            detector = detectors[current_detector]
            logger.info(f"Using {current_detector} for detection...")
            
            try:
                detection_result = process_with_detector(detector, bounds, current_detector)
                if detection_result:
                    return create_success_response(detection_result, area_info, current_detector)
                else:
                    logger.warning(f"Detector {current_detector} returned no result, falling back")
                    
            except Exception as detector_error:
                logger.error(f"{current_detector} failed: {detector_error}")
                # Update health status
                detector_health[current_detector] = 'unstable'
        
        # Fallback to dummy mode
        logger.info("Falling back to enhanced dummy detection mode")
        detection_result = process_region_enhanced_dummy(bounds)
        return create_success_response(detection_result, area_info, 'enhanced_dummy_fallback')
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": f"Processing failed: {str(e)}",
            "type": type(e).__name__
        }), 500

@app.route('/download_waypoints', methods=['POST'])
def download_waypoints():
    """Download waypoints file in QGC WPL 110 format"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        if 'bounds' not in data:
            return jsonify({"error": "No bounds provided"}), 400
        
        bounds = data['bounds']
        trees = data.get('trees', [])
        
        # If no trees provided, use current detector to get trees
        if not trees and current_detector and current_detector in detectors and current_detector != 'dummy':
            detector = detectors[current_detector]
            trees, _ = detector.detect_trees(bounds)
        elif not trees:
            # Use enhanced dummy
            detection_result = process_region_enhanced_dummy(bounds)
            trees = detection_result['trees']
        
        # Create waypoints content
        waypoints_content = create_waypoints_file(trees, bounds)
        
        # Create response with waypoints file
        response = Response(
            waypoints_content,
            mimetype='text/plain',
            headers={
                'Content-Disposition': 'attachment;filename=mission.waypoints',
                'Content-Type': 'text/plain'
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating waypoints file: {e}")
        return jsonify({"error": f"Failed to generate waypoints file: {str(e)}"}), 500

@app.route('/get_waypoints_data', methods=['POST'])
def get_waypoints_data():
    """Get waypoints data as JSON for preview"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        if 'bounds' not in data:
            return jsonify({"error": "No bounds provided"}), 400
        
        bounds = data['bounds']
        trees = data.get('trees', [])
        
        # If no trees provided, use current detector to get trees
        if not trees and current_detector and current_detector in detectors and current_detector != 'dummy':
            detector = detectors[current_detector]
            trees, _ = detector.detect_trees(bounds)
        elif not trees:
            # Use enhanced dummy
            detection_result = process_region_enhanced_dummy(bounds)
            trees = detection_result['trees']
        
        # Create waypoints content
        waypoints_content = create_waypoints_file(trees, bounds)
        
        # Parse waypoints for JSON response
        waypoints_lines = waypoints_content.split('\n')[1:]  # Skip header
        waypoints_data = []
        
        for line in waypoints_lines:
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 11:
                    waypoint = {
                        'index': int(parts[0]),
                        'current_wp': int(parts[1]),
                        'coord_frame': int(parts[2]),
                        'command': int(parts[3]),
                        'param1': float(parts[4]),
                        'param2': float(parts[5]),
                        'param3': float(parts[6]),
                        'param4': float(parts[7]),
                        'lat': float(parts[8]),
                        'lng': float(parts[9]),
                        'alt': float(parts[10]),
                        'auto_continue': int(parts[11]) if len(parts) > 11 else 1
                    }
                    waypoints_data.append(waypoint)
        
        return jsonify({
            "waypoints_count": len(waypoints_data),
            "waypoints": waypoints_data,
            "waypoints_file_preview": waypoints_content,
            "trees_count": len(trees)
        })
        
    except Exception as e:
        logger.error(f"Error getting waypoints data: {e}")
        return jsonify({"error": f"Failed to get waypoints data: {str(e)}"}), 500

def validate_bounds(bounds):
    """Validate bounds structure comprehensively"""
    errors = []
    
    required_keys = ['_southWest', '_northEast']
    for key in required_keys:
        if key not in bounds:
            errors.append(f"Missing {key} in bounds")
            continue
            
        point = bounds[key]
        if 'lat' not in point:
            errors.append(f"Missing lat in {key}")
        if 'lng' not in point:
            errors.append(f"Missing lng in {key}")
    
    # Check coordinate validity
    if not errors:
        try:
            sw = bounds['_southWest']
            ne = bounds['_northEast']
            
            if not (-90 <= sw['lat'] <= 90): errors.append("SouthWest lat out of range")
            if not (-180 <= sw['lng'] <= 180): errors.append("SouthWest lng out of range")
            if not (-90 <= ne['lat'] <= 90): errors.append("NorthEast lat out of range")
            if not (-180 <= ne['lng'] <= 180): errors.append("NorthEast lng out of range")
            
            if ne['lat'] <= sw['lat']: errors.append("NorthEast lat must be greater than SouthWest lat")
            if ne['lng'] <= sw['lng']: errors.append("NorthEast lng must be greater than SouthWest lng")
            
        except Exception as e:
            errors.append(f"Error validating coordinates: {str(e)}")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def calculate_area_info(bounds):
    """Calculate area information"""
    lat_diff = bounds['_northEast']['lat'] - bounds['_southWest']['lat']
    lng_diff = bounds['_northEast']['lng'] - bounds['_southWest']['lng']
    area_hectares = abs(lat_diff * lng_diff * 10000)
    
    return {
        'area_hectares': area_hectares,
        'lat_diff': lat_diff,
        'lng_diff': lng_diff
    }

def process_with_detector(detector, bounds, detector_name):
    """Process region with specific detector"""
    trees, satellite_image = detector.detect_trees(bounds)
    
    # Create visualization
    if hasattr(detector, 'create_detection_visualization'):
        visualization_image = detector.create_detection_visualization(bounds, trees, satellite_image)
    else:
        # Fallback visualization
        visualization_image = satellite_image
    
    # Convert to base64
    if hasattr(detector, 'image_to_base64'):
        visualization = detector.image_to_base64(visualization_image)
    else:
        buffered = io.BytesIO()
        if hasattr(visualization_image, 'save'):
            visualization_image.save(buffered, format="PNG")
        else:
            # Assume it's a numpy array
            from PIL import Image
            pil_image = Image.fromarray(visualization_image)
            pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        visualization = f"data:image/png;base64,{img_str}"
    
    return {
        'trees': trees,
        'visualization': visualization,
        'detector_name': detector_name
    }

def create_success_response(detection_result, area_info, detector_name):
    """Create success response with consistent structure"""
    trees = detection_result['trees']
    visualization = detection_result['visualization']
    
    # Create both mission plan and waypoints file
    mission_plan = create_mission_plan(trees, area_info)
    waypoints_content = create_waypoints_file(trees, area_info)
    
    # Calculate statistics
    statistics = calculate_statistics(trees, area_info, detector_name)
    
    return jsonify({
        "message": f"{detector_name.replace('_', ' ').title()} detected {len(trees)} palm trees in {area_info['area_hectares']:.2f} hectares",
        "statistics": statistics,
        "visualization": visualization,
        "plan": mission_plan,
        "waypoints_file": waypoints_content,
        "waypoints_count": len(trees) * 2 + 1,  # Each tree has waypoint + loiter, plus home
        "detections_sample": trees[:5] if trees else [],
        "detector_used": detector_name,
        "endpoints": {
            "download_waypoints": "POST /download_waypoints",
            "get_waypoints_data": "POST /get_waypoints_data"
        }
    })

def calculate_statistics(trees, area_info, detector_name):
    """Calculate detection statistics"""
    import numpy as np
    confidences = [tree['confidence'] for tree in trees] if trees else []
    avg_confidence = np.mean(confidences) if confidences else 0
    
    return {
        "trees_detected": len(trees),
        "area_hectares": area_info['area_hectares'],
        "tree_density": len(trees) / area_info['area_hectares'] if area_info['area_hectares'] > 0 else 0,
        "average_confidence": float(avg_confidence),
        "confidence_std": float(np.std(confidences)) if confidences else 0,
        "detection_model": detector_name,
        "area_coverage_km2": area_info['area_hectares'] / 100
    }

def process_region_enhanced_dummy(bounds):
    """Enhanced dummy implementation with realistic data"""
    
    area_info = calculate_area_info(bounds)
    area_hectares = area_info['area_hectares']
    
    # Generate realistic number of trees based on area
    # Palm plantations typically have 120-180 trees per hectare
    trees_per_hectare = random.randint(120, 180)
    num_trees = max(10, min(500, int(area_hectares * trees_per_hectare)))
    
    trees = []
    
    # Create clustered distribution for realism
    num_clusters = max(1, num_trees // 50)
    cluster_centers = []
    
    for _ in range(num_clusters):
        center_lat = bounds['_southWest']['lat'] + random.random() * area_info['lat_diff']
        center_lng = bounds['_southWest']['lng'] + random.random() * area_info['lng_diff']
        cluster_centers.append((center_lat, center_lng))
    
    trees_placed = 0
    for center_lat, center_lng in cluster_centers:
        cluster_size = random.randint(num_trees // (2 * num_clusters), num_trees // num_clusters)
        
        for _ in range(cluster_size):
            if trees_placed >= num_trees:
                break
                
            # Add some variation around cluster center
            lat = center_lat + (random.random() - 0.5) * area_info['lat_diff'] * 0.2
            lng = center_lng + (random.random() - 0.5) * area_info['lng_diff'] * 0.2
            
            # Ensure within bounds
            lat = max(bounds['_southWest']['lat'], min(bounds['_northEast']['lat'], lat))
            lng = max(bounds['_southWest']['lng'], min(bounds['_northEast']['lng'], lng))
            
            trees.append({
                'id': trees_placed + 1,
                'lat': lat,
                'lng': lng,
                'confidence': random.uniform(0.7, 0.95),
                'class': 'palm_tree',
                'model_source': 'enhanced_dummy'
            })
            trees_placed += 1
    
    # Add remaining trees randomly
    while trees_placed < num_trees:
        lat = bounds['_southWest']['lat'] + random.random() * area_info['lat_diff']
        lng = bounds['_southWest']['lng'] + random.random() * area_info['lng_diff']
        
        trees.append({
            'id': trees_placed + 1,
            'lat': lat,
            'lng': lng,
            'confidence': random.uniform(0.7, 0.95),
            'class': 'palm_tree',
            'model_source': 'enhanced_dummy'
        })
        trees_placed += 1
    
    # Create enhanced visualization
    visualization = create_enhanced_dummy_visualization(bounds, trees, area_info)
    
    return {
        'trees': trees,
        'visualization': visualization
    }

def create_enhanced_dummy_visualization(bounds, trees, area_info):
    """Create enhanced dummy visualization"""
    import cv2
    from PIL import Image
    import numpy as np
    
    image_size = (800, 600)
    img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 200
    
    # Draw area boundary
    cv2.rectangle(img, (50, 50), (750, 550), (0, 100, 0), 3)
    
    # Draw grid for plantation pattern
    for i in range(1, 8):
        cv2.line(img, (50 + i*100, 50), (50 + i*100, 550), (180, 180, 180), 1)
    for j in range(1, 5):
        cv2.line(img, (50, 50 + j*100), (750, 50 + j*100), (180, 180, 180), 1)
    
    # Draw trees as circles with clustering
    for tree in trees:
        # Normalize coordinates to image space
        lat_norm = (tree['lat'] - bounds['_southWest']['lat']) / area_info['lat_diff']
        lng_norm = (tree['lng'] - bounds['_southWest']['lng']) / area_info['lng_diff']
        
        x = int(50 + lng_norm * 700)
        y = int(50 + lat_norm * 500)
        
        # Color based on confidence
        if tree['confidence'] > 0.8:
            color = (0, 200, 0)  # Green - high confidence
        elif tree['confidence'] > 0.6:
            color = (0, 150, 100)  # Teal - medium confidence
        else:
            color = (0, 100, 150)  # Blue-green - low confidence
            
        cv2.circle(img, (x, y), 4, color, -1)
        cv2.circle(img, (x, y), 4, (255, 255, 255), 1)
    
    # Add informative text
    cv2.putText(img, f"Enhanced Dummy Visualization - {len(trees)} Trees Detected", 
               (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, f"Area: {area_info['area_hectares']:.2f} hectares | Density: {len(trees)/area_info['area_hectares']:.1f} trees/ha", 
               (50, 570), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
    cv2.putText(img, "Using simulated data - Configure Roboflow API for real detection", 
               (50, 590), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 100, 100), 1)
    
    # Convert to base64
    pil_image = Image.fromarray(img)
    buffered = io.BytesIO()
    pil_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"

@app.route('/process_region_dummy', methods=['POST'])
def process_region_dummy():
    """Explicit dummy endpoint for testing"""
    try:
        data = request.get_json()
        if not data or 'bounds' not in data:
            return jsonify({"error": "No bounds provided"}), 400
            
        bounds = data['bounds']
        detection_result = process_region_enhanced_dummy(bounds)
        area_info = calculate_area_info(bounds)
        
        return create_success_response(detection_result, area_info, 'explicit_dummy')
        
    except Exception as e:
        logger.error(f"Dummy processing failed: {str(e)}")
        return jsonify({"error": f"Dummy processing failed: {str(e)}"}), 500

if __name__ == '__main__':
    print("🌴 Palm Tree Detection Backend - Enhanced with Custom YOLO")
    print("=" * 60)
    
    # Display initialization status
    for model_name, health in detector_health.items():
        status_icon = "✅" if health in ['healthy', 'tested'] else "⚠️" if health == 'unstable' else "❌"
        print(f"{status_icon} {model_name}: {health}")
    
    if 'local_custom' in detectors:
        print(f"\n✅ Custom YOLO Model: READY (models/best.pt)")
        print(f"   Model: Your trained YOLO model")
        print(f"   Status: {detector_health.get('local_custom', 'unknown')}")
    
    if 'roboflow_workflow' in detectors:
        print(f"\n✅ Roboflow Workflow: READY (inference-sdk)")
        print(f"   Workspace: {ROBOFLOW_CONFIG['WORKSPACE']}")
        print(f"   Workflow: {ROBOFLOW_CONFIG['WORKFLOW_ID']}")
    else:
        print(f"\n❌ Roboflow Workflow: NOT AVAILABLE")
        if not detector_modules.get('roboflow_workflow', False):
            print("   - inference-sdk not installed or import failed")
            print("   - Run: pip install inference-sdk")
        elif ROBOFLOW_CONFIG["API_KEY"] == "YOUR_VALID_API_KEY_HERE":
            print("   - API key not configured")
        else:
            print("   - API key may be invalid or initialization failed")
    
    print(f"\n📡 Available models: {list(detectors.keys())}")
    print(f"🎯 Current model: {current_detector}")
    
    print("\n🚀 Server running on http://localhost:5000")
    print("   Endpoints:")
    print("   - GET  /health")
    print("   - GET  /model_info") 
    print("   - POST /process_region")
    print("   - POST /switch_model")
    print("   - POST /update_api_key")
    
    app.run(debug=True, host='0.0.0.0', port=5000)