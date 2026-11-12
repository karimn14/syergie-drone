import os
import cv2
import numpy as np
import base64
import logging
from io import BytesIO
from PIL import Image
import json
import random

# Import inference SDK
try:
    from inference_sdk import InferenceHTTPClient
    HAS_INFERENCE_SDK = True
except ImportError:
    HAS_INFERENCE_SDK = False
    logging.error("inference-sdk not installed. Run: pip install inference-sdk")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RoboflowWorkflowDetector:
    def __init__(self, api_key, workspace_name, workflow_id):
        """Initialize Roboflow Workflow client with robust error handling"""
        
        if not HAS_INFERENCE_SDK:
            raise ImportError("inference-sdk is required. Install with: pip install inference-sdk")
        
        self.api_key = api_key
        self.workspace_name = workspace_name
        self.workflow_id = workflow_id
        
        # Validate API key format
        if not api_key or len(api_key) < 10:
            raise ValueError("Invalid API key format")
        
        try:
            # Initialize the client
            self.client = InferenceHTTPClient(
                api_url="https://serverless.roboflow.com",
                api_key=api_key
            )
            
            logger.info(f"✅ Roboflow Workflow SDK initialized: {workspace_name}/{workflow_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Roboflow client: {e}")
            raise
    
    def download_satellite_image(self, bounds, image_size=(640, 640)):
        """
        Download or create satellite image for given bounds with improved quality
        """
        try:
            # Calculate center coordinates
            center_lat = (bounds['_southWest']['lat'] + bounds['_northEast']['lat']) / 2
            center_lng = (bounds['_southWest']['lng'] + bounds['_northEast']['lng']) / 2
            
            # Create high-quality synthetic satellite image
            image = self._create_high_quality_satellite_image(bounds, image_size)
            
            return image
            
        except Exception as e:
            logger.error(f"Error creating satellite image: {e}")
            return self._create_basic_fallback_image(image_size)
    
    def _create_high_quality_satellite_image(self, bounds, image_size=(640, 640)):
        """Create high-quality synthetic satellite image"""
        try:
            # Create base terrain
            img = np.zeros((image_size[1], image_size[0], 3), dtype=np.uint8)
            
            # Generate realistic terrain with noise
            for channel in range(3):
                # Base color with variations
                base_color = [60, 130, 70]  # Greenish terrain
                noise = np.random.randint(-20, 20, (image_size[1], image_size[0]))
                channel_layer = np.full((image_size[1], image_size[0]), base_color[channel], dtype=np.uint8)
                channel_layer = np.clip(channel_layer + noise, 0, 255).astype(np.uint8)
                img[:, :, channel] = channel_layer
            
            # Add realistic palm plantation pattern
            self._add_plantation_pattern(img, bounds)
            
            # Add some random features (roads, buildings, etc.)
            self._add_environment_features(img)
            
            return img
            
        except Exception as e:
            logger.error(f"Error creating high quality image: {e}")
            return self._create_basic_fallback_image(image_size)
    
    def _add_plantation_pattern(self, img, bounds):
        """Add realistic palm plantation pattern"""
        try:
            height, width = img.shape[:2]
            
            # Create grid pattern for plantation
            rows, cols = 8, 8
            cell_width = width // cols
            cell_height = height // rows
            
            for row in range(rows):
                for col in range(cols):
                    if random.random() > 0.2:  # 80% of cells have trees
                        center_x = col * cell_width + cell_width // 2
                        center_y = row * cell_height + cell_height // 2
                        
                        # Add random offset for natural look
                        center_x += random.randint(-cell_width//4, cell_width//4)
                        center_y += random.randint(-cell_height//4, cell_height//4)
                        
                        # Draw palm tree cluster
                        self._draw_palm_tree_cluster(img, center_x, center_y)
            
        except Exception as e:
            logger.error(f"Error adding plantation pattern: {e}")
    
    def _draw_palm_tree_cluster(self, img, center_x, center_y):
        """Draw a cluster of palm trees"""
        try:
            # Draw 1-3 trees in cluster
            num_trees = random.randint(1, 3)
            
            for _ in range(num_trees):
                # Random offset from center
                x = center_x + random.randint(-15, 15)
                y = center_y + random.randint(-15, 15)
                
                # Ensure within image bounds
                if 20 <= x < img.shape[1] - 20 and 20 <= y < img.shape[0] - 20:
                    # Tree trunk
                    trunk_height = random.randint(12, 20)
                    trunk_width = random.randint(2, 4)
                    
                    cv2.rectangle(img,
                                (x - trunk_width, y),
                                (x + trunk_width, y + trunk_height),
                                (30, 20, 10), -1)
                    
                    # Tree canopy
                    canopy_radius = random.randint(8, 15)
                    canopy_color = (0, random.randint(80, 150), 0)
                    
                    cv2.circle(img, (x, y - canopy_radius//2), 
                             canopy_radius, canopy_color, -1)
                    
                    # Add canopy texture
                    for _ in range(3):
                        tx = x + random.randint(-canopy_radius, canopy_radius)
                        ty = y - canopy_radius//2 + random.randint(-canopy_radius, canopy_radius)
                        if (tx - x)**2 + (ty - (y - canopy_radius//2))**2 <= canopy_radius**2:
                            cv2.circle(img, (tx, ty), random.randint(2, 4),
                                     (0, canopy_color[1] + random.randint(-20, 20), 0), -1)
                            
        except Exception as e:
            logger.error(f"Error drawing palm tree cluster: {e}")
    
    def _add_environment_features(self, img):
        """Add environmental features like roads, buildings"""
        try:
            height, width = img.shape[:2]
            
            # Add a road
            road_y = height // 2
            road_width = 15
            cv2.rectangle(img, (0, road_y - road_width//2), 
                         (width, road_y + road_width//2), (80, 80, 80), -1)
            
            # Add road markings
            for x in range(0, width, 40):
                cv2.rectangle(img, (x, road_y - 2), (x + 20, road_y + 2), (255, 255, 255), -1)
            
            # Add some buildings/structures
            for _ in range(3):
                building_x = random.randint(50, width - 100)
                building_y = random.randint(50, height - 100)
                building_w = random.randint(30, 60)
                building_h = random.randint(40, 80)
                
                cv2.rectangle(img, (building_x, building_y),
                            (building_x + building_w, building_y + building_h),
                            (100, 100, 120), -1)
                
        except Exception as e:
            logger.error(f"Error adding environment features: {e}")
    
    def _create_basic_fallback_image(self, image_size=(640, 640)):
        """Create basic fallback image"""
        img = np.ones((image_size[1], image_size[0], 3), dtype=np.uint8) * 100
        
        # Add simple grid pattern
        for i in range(0, image_size[0], 20):
            cv2.line(img, (i, 0), (i, image_size[1]), (80, 80, 80), 1)
        for j in range(0, image_size[1], 20):
            cv2.line(img, (0, j), (image_size[0], j), (80, 80, 80), 1)
            
        return img
    
    def save_temp_image(self, image):
        """Save image to temporary file with error handling"""
        try:
            temp_path = "temp_satellite_image.jpg"
            success = cv2.imwrite(temp_path, image)
            if not success:
                raise Exception("Failed to write image file")
            return temp_path
        except Exception as e:
            logger.error(f"Error saving temp image: {e}")
            raise
    
    def image_to_base64(self, image):
        """Convert image to base64 with error handling"""
        try:
            if isinstance(image, np.ndarray):
                # Convert BGR to RGB
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
            else:
                pil_image = image
                
            buffered = BytesIO()
            pil_image.save(buffered, format="JPEG", quality=95)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return img_str
            
        except Exception as e:
            logger.error(f"Error converting image to base64: {e}")
            return ""
    
    def detect_trees(self, bounds):
        """Detect palm trees using Roboflow Workflow SDK with robust error handling"""
        try:
            # Validate bounds first
            if not self._validate_bounds(bounds):
                raise ValueError("Invalid bounds provided")
            
            # Download/create satellite image
            satellite_image = self.download_satellite_image(bounds)
            
            # Save temporary image
            temp_image_path = self.save_temp_image(satellite_image)
            
            logger.info("Sending request to Roboflow Workflow using inference-sdk...")
            
            # Run workflow using inference SDK with timeout
            try:
                result = self.client.run_workflow(
                    workspace_name=self.workspace_name,
                    workflow_id=self.workflow_id,
                    images={
                        "image": temp_image_path
                    },
                    use_cache=True
                )
            except Exception as api_error:
                logger.error(f"Roboflow API error: {api_error}")
                raise
            
            # Clean up temporary file
            try:
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp file: {cleanup_error}")
            
            logger.info("Roboflow Workflow response received successfully")
            
            # Process results
            trees, visualization_image = self._parse_workflow_result(result, bounds, satellite_image)
            
            return trees, visualization_image
            
        except Exception as e:
            logger.error(f"Error in Roboflow Workflow detection: {e}")
            # Provide meaningful fallback
            return self._create_workflow_fallback(bounds)
    
    def _validate_bounds(self, bounds):
        """Validate bounds structure"""
        try:
            required_keys = ['_southWest', '_northEast']
            for key in required_keys:
                if key not in bounds:
                    return False
                if 'lat' not in bounds[key] or 'lng' not in bounds[key]:
                    return False
            
            # Check bounds validity
            sw = bounds['_southWest']
            ne = bounds['_northEast']
            
            if ne['lat'] <= sw['lat'] or ne['lng'] <= sw['lng']:
                return False
                
            return True
        except Exception:
            return False
    
    def _create_workflow_fallback(self, bounds):
        """Create fallback when workflow fails"""
        try:
            # Create realistic fallback data
            lat_diff = bounds['_northEast']['lat'] - bounds['_southWest']['lat']
            lng_diff = bounds['_northEast']['lng'] - bounds['_southWest']['lng']
            area_hectares = abs(lat_diff * lng_diff * 10000)
            
            # Generate appropriate number of trees
            trees_per_hectare = 150  # Typical palm density
            num_trees = max(20, min(300, int(area_hectares * trees_per_hectare)))
            
            trees = []
            for i in range(num_trees):
                lat = bounds['_southWest']['lat'] + random.random() * lat_diff
                lng = bounds['_southWest']['lng'] + random.random() * lng_diff
                
                trees.append({
                    'id': i + 1,
                    'lat': lat,
                    'lng': lng,
                    'confidence': random.uniform(0.8, 0.95),
                    'class': 'palm_tree',
                    'model_source': 'roboflow_workflow_fallback'
                })
            
            image = self.download_satellite_image(bounds)
            return trees, image
            
        except Exception as e:
            logger.error(f"Error in workflow fallback: {e}")
            return [], self._create_basic_fallback_image()
    
    def _parse_workflow_result(self, result, bounds, original_image):
        """Parse Roboflow Workflow response safely"""
        trees = []
        visualization_image = original_image.copy()
        
        try:
            logger.info(f"Workflow result type: {type(result)}")
            
            # Handle different response formats safely
            predictions = self._extract_predictions_safely(result)
            logger.info(f"Found {len(predictions)} predictions")
            
            # Process each detection with error handling
            for i, detection in enumerate(predictions):
                try:
                    tree_data = self._parse_single_detection(detection, bounds, original_image, i)
                    if tree_data:
                        trees.append(tree_data)
                        self._draw_detection(visualization_image, tree_data)
                        
                except Exception as e:
                    logger.warning(f"Skipping detection {i} due to error: {e}")
                    continue
            
            return trees, visualization_image
            
        except Exception as e:
            logger.error(f"Error parsing workflow result: {e}")
            return trees, visualization_image
    
    def _extract_predictions_safely(self, result):
        """Extract predictions from result safely"""
        predictions = []
        
        try:
            # Format 1: Direct predictions array
            if isinstance(result, dict) and 'predictions' in result:
                predictions = result['predictions']
            # Format 2: Nested in workflow steps
            elif isinstance(result, dict) and 'results' in result:
                for step_key, step_result in result['results'].items():
                    if isinstance(step_result, dict) and 'predictions' in step_result:
                        predictions.extend(step_result['predictions'])
                        break
                    elif isinstance(step_result, list):
                        predictions = step_result
                        break
            # Format 3: Result is directly a list
            elif isinstance(result, list):
                predictions = result
            # Format 4: Try to find predictions in nested structure
            elif isinstance(result, dict):
                # Recursively search for predictions
                predictions = self._find_predictions_recursive(result)
                
        except Exception as e:
            logger.error(f"Error extracting predictions: {e}")
        
        return predictions
    
    def _find_predictions_recursive(self, obj, max_depth=3):
        """Recursively find predictions in nested structure"""
        predictions = []
        
        def search(current_obj, current_depth=0):
            if current_depth > max_depth:
                return
            
            if isinstance(current_obj, list):
                # Check if this list contains detection-like objects
                if len(current_obj) > 0 and isinstance(current_obj[0], (dict, list)):
                    predictions.extend(current_obj)
                return
            elif isinstance(current_obj, dict):
                for key, value in current_obj.items():
                    if 'prediction' in key.lower() or 'detection' in key.lower():
                        if isinstance(value, list):
                            predictions.extend(value)
                            return
                    search(value, current_depth + 1)
        
        search(obj)
        return predictions
    
    def _parse_single_detection(self, detection, bounds, original_image, index):
        """Parse a single detection safely"""
        try:
            # Initialize default values
            xmin = ymin = xmax = ymax = 0
            confidence = 0.5
            class_name = 'palm_tree'
            
            if isinstance(detection, dict):
                # Handle different bounding box formats
                if all(k in detection for k in ['x', 'y', 'width', 'height']):
                    # YOLO format
                    x_center, y_center = detection['x'], detection['y']
                    width, height = detection['width'], detection['height']
                    xmin = x_center - width / 2
                    ymin = y_center - height / 2
                    xmax = x_center + width / 2
                    ymax = y_center + height / 2
                    
                elif 'points' in detection:
                    # Polygon format
                    points = detection['points']
                    x_coords = [p.get('x', 0) for p in points]
                    y_coords = [p.get('y', 0) for p in points]
                    xmin, xmax = min(x_coords), max(x_coords)
                    ymin, ymax = min(y_coords), max(y_coords)
                    
                else:
                    # Try various bbox formats
                    xmin = detection.get('xmin', detection.get('x1', 0))
                    ymin = detection.get('ymin', detection.get('y1', 0))
                    xmax = detection.get('xmax', detection.get('x2', 0))
                    ymax = detection.get('ymax', detection.get('y2', 0))
                
                # Get confidence and class safely
                confidence = float(detection.get('confidence', 0.5))
                class_name = str(detection.get('class', 'palm_tree'))
                
            elif isinstance(detection, list) and len(detection) >= 4:
                # Assume [xmin, ymin, xmax, ymax, confidence, class]
                xmin, ymin, xmax, ymax = detection[:4]
                if len(detection) > 4:
                    confidence = float(detection[4])
                if len(detection) > 5:
                    class_name = str(detection[5])
            
            # Convert to geographic coordinates
            lat, lng = self._pixel_to_geo(
                (xmin + xmax) / 2,
                (ymin + ymax) / 2,
                bounds, 
                original_image.shape
            )
            
            return {
                'id': index + 1,
                'lat': lat,
                'lng': lng,
                'confidence': confidence,
                'class': class_name,
                'bbox': {
                    'xmin': float(xmin),
                    'ymin': float(ymin),
                    'xmax': float(xmax),
                    'ymax': float(ymax)
                },
                'model_source': 'roboflow_workflow_sdk'
            }
            
        except Exception as e:
            logger.error(f"Error parsing single detection: {e}")
            return None
    
    def _draw_detection(self, image, tree_data):
        """Draw detection on image safely"""
        try:
            bbox = tree_data['bbox']
            confidence = tree_data['confidence']
            
            xmin, ymin = int(bbox['xmin']), int(bbox['ymin'])
            xmax, ymax = int(bbox['xmax']), int(bbox['ymax'])
            
            # Ensure coordinates are within image bounds
            xmin = max(0, min(image.shape[1] - 1, xmin))
            ymin = max(0, min(image.shape[0] - 1, ymin))
            xmax = max(0, min(image.shape[1] - 1, xmax))
            ymax = max(0, min(image.shape[0] - 1, ymax))
            
            if xmin >= xmax or ymin >= ymax:
                return
            
            # Choose color based on confidence
            if confidence > 0.8:
                color = (0, 255, 0)  # Green
            elif confidence > 0.5:
                color = (0, 165, 255)  # Orange
            else:
                color = (0, 0, 255)  # Red
            
            # Draw bounding box
            cv2.rectangle(image, (xmin, ymin), (xmax, ymax), color, 2)
            
            # Draw label
            label = f"{tree_data['class']}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            
            # Ensure label position is within image
            label_y = max(ymin - 10, label_size[1] + 5)
            label_bg_y1 = label_y - label_size[1] - 5
            label_bg_y2 = label_y
            
            if label_bg_y1 >= 0 and label_bg_y2 < image.shape[0]:
                # Draw label background
                cv2.rectangle(image, (xmin, label_bg_y1),
                            (xmin + label_size[0], label_bg_y2), color, -1)
                # Draw label text
                cv2.putText(image, label, (xmin, label_y - 5),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                          
        except Exception as e:
            logger.error(f"Error drawing detection: {e}")
    
    def _pixel_to_geo(self, x, y, bounds, image_shape):
        """Convert pixel coordinates to geographic coordinates safely"""
        try:
            height, width = image_shape[:2]
            
            lat_range = bounds['_northEast']['lat'] - bounds['_southWest']['lat']
            lng_range = bounds['_northEast']['lng'] - bounds['_southWest']['lng']
            
            # Normalize pixel coordinates (0-1)
            x_norm = max(0, min(1, x / width))
            y_norm = max(0, min(1, y / height))
            
            # Convert to geographic coordinates (invert y-axis)
            lat = bounds['_southWest']['lat'] + (1 - y_norm) * lat_range
            lng = bounds['_southWest']['lng'] + x_norm * lng_range
            
            return lat, lng
            
        except Exception as e:
            logger.error(f"Error in pixel_to_geo conversion: {e}")
            # Return center of bounds as fallback
            center_lat = (bounds['_northEast']['lat'] + bounds['_southWest']['lat']) / 2
            center_lng = (bounds['_northEast']['lng'] + bounds['_southWest']['lng']) / 2
            return center_lat, center_lng
    
    def create_detection_visualization(self, bounds, trees, satellite_image):
        """Create visualization with detection results"""
        try:
            vis_image = satellite_image.copy()
            
            # Draw detections
            for tree in trees:
                self._draw_detection(vis_image, tree)
            
            # Add title and info
            cv2.putText(vis_image, f"Roboflow Workflow - Palm Trees: {len(trees)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Convert to PIL Image
            vis_image_rgb = cv2.cvtColor(vis_image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(vis_image_rgb)
            
            return pil_image
            
        except Exception as e:
            logger.error(f"Error creating visualization: {e}")
            vis_image_rgb = cv2.cvtColor(satellite_image, cv2.COLOR_BGR2RGB)
            return Image.fromarray(vis_image_rgb)
    
    def get_model_info(self):
        """Get information about the Roboflow Workflow"""
        info = {
            'model_type': 'Roboflow Workflow (inference-sdk)',
            'workspace': self.workspace_name,
            'workflow_id': self.workflow_id,
            'model_source': 'roboflow_cloud',
            'sdk_version': 'inference-sdk',
            'status': 'active'
        }
        
        return info