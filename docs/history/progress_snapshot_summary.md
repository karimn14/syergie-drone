# Syergie Drone Progress

Multi-project workspace for agricultural drone development. This repo contains:
- A full Jetson + Pixhawk + Arduino stack (drone_sawit)
- A ROS-based demo sprint (new_plan_2_9)
- A satellite planning web app (palm_planner)
- Mechanical CAD assets (mekanik)

This README expands every subproject section with setup, runbook, outputs, and risks so you can decide what to continue next.

## Decision guide (which subproject to continue)

If you need a field-ready flight stack or a full end-to-end mission pipeline:
- Continue drone_sawit
- Requires Jetson + Pixhawk + Arduino and MAVSDK setup
- Most complete module coverage but also the most hardware dependent

If you need a fast demo with clear docs and ROS integration:
- Continue new_plan_2_9
- Strong runbooks for a 6-day sprint and ROS launch flows
- Focused on perception + spray logic, not full autonomy

If you need a planning UI or a laptop-runnable project:
- Continue palm_planner
- Runs on a normal workstation with Flask + React
- Best choice if hardware is not available now

If you are focused on hardware and payload design:
- Continue mekanik
- CAD assets only, no runtime code

## Repository evaluation (high level)

Overall maturity:
- Prototype / research stage. Many modules are functional but some are placeholders.
- Hardware integration paths are documented, but automated tests are minimal.

Risks and gaps:
- Some scripts are stubs (auto_mission_planner.py, mission_state_machine.py, compliance.py).
- vision_recheck.py expects BloomClassifier.infer to return labels and results, but ai_inference.py returns only labels.
- design_review.md appears to have encoding issues (garbled headings).

Recommendation:
- Pick one stack to focus on. The drone_sawit and new_plan_2_9 stacks overlap in purpose but differ in tooling (FastAPI vs ROS).
- If you need a working demo quickly, start with new_plan_2_9.
- If you want the full production pipeline, use drone_sawit.

## Workspace map

- drone_sawit/ - production stack: Jetson (AI and mission logic), Pixhawk (flight), Arduino (sprayer)
- new_plan_2_9/ - ROS-based pollination system (2026 sprint)
- palm_planner/ - satellite tree detection and route planning web app
- mekanik/ - mechanical CAD models and assemblies

Notes:
- drone_sawit/myenv/ is a bundled Python virtual environment and is not part of the application code.
- palm_planner/backend/datasets/ contains datasets and labels, not application logic.
- mekanik/ contains CAD and binary assets, not code.

## drone_sawit (Jetson + Pixhawk + Arduino stack)

### What this does
Autonomous pollination and spraying system for palm plantations. The Jetson handles AI, mission planning, and telemetry. Pixhawk executes the flight mission and servo outputs. Arduino controls sprayer hardware and diagnostics.

### Architecture and data flow

Data and control flow (typical mission):

1) AI detections -> predicted_trees.geojson
2) ai_output_loader -> list of target trees
3) route_generator or enhanced_route_generator -> QGC .plan
4) spray_command_mapper -> spray_commands_linked.csv
5) upload_plan_mission or QGC -> Pixhawk mission
6) px4_spray_sync -> trigger spray based on GPS proximity
7) logs -> mission.log, spray_log.csv, coverage_report.png, mission_report.pdf

### Key entry points

- orchestrator.py - runs preflight checks, starts Jetson backend, prompts plan upload
- jetson/main.py - FastAPI dashboard and REST API on port 8000
- jetson/dashboard_server.py - simple Flask dashboard on port 8080
- jetson/main_launcher.py - end-to-end mission pipeline (AI load -> plan -> spray map -> PX4 sync)

### Jetson modules (by function)

Mission planning and routing
- jetson/ai_output_loader.py - loads predicted_trees.geojson and filters blooming female trees
- jetson/route_generator.py - builds a QGroundControl .plan from waypoints
- jetson/enhanced_route_generator.py - spline-smoothed route generator
- jetson/delay_plan_generator.py - inserts MAV_CMD_NAV_DELAY after waypoints
- jetson/auto_mission_planner.py - placeholder image-based planner that writes auto.plan
- jetson/battery_route_splitter.py - splits waypoints and emits segmented .plan files
- jetson/mission_config_loader.py - loads mission_config.yaml
- jetson/mission_state_machine.py - minimal FSM stub for mission flow
- jetson/mission_simulator.py - simulates spray events from spray_commands_linked.csv

Spray control and AI
- jetson/ai_inference.py - BloomClassifier using a PyTorch model
- jetson/spray_command_mapper.py - maps tree age to spray duration via pollen_dosage_table.csv
- jetson/spray_command_mapper_confidence.py - scales duration by confidence
- jetson/px4_spray_sync.py - triggers spray based on GPS proximity using MAVSDK and serial
- jetson/retry_logic_spray.py - retries failed spray attempts
- jetson/vision_recheck.py - optional camera confirmation before spray
- jetson/wind_compensator.py - adjusts duration and gimbal angle by wind
- jetson/tree_proximity_checker.py - reads multiple proximity sensors over serial
- jetson/vio_fallback.py - visual inertial fallback using optical flow

Flight and Pixhawk integration
- jetson/auto_takeoff_landing.py - MAVSDK takeoff, land, and dock helpers
- jetson/plan_uploader.py - invokes QGroundControl to load a .plan
- jetson/upload_plan_mission.py - uploads a .plan via MAVSDK
- jetson/upload_segmented_missions.py - uploads multiple .plan files
- jetson/upload_px4_params.py - uploads a .param file via MAVSDK
- jetson/px4_timesync.py - logs GPS_RAW_INT time from PX4
- jetson/send_telemetry_to_pixhawk.py - sends custom MAVLink named_value telemetry

Safety, diagnostics, and health
- jetson/preflight_diagnostics.py - camera, Arduino, and GPS checks
- jetson/health_monitor.py - heartbeat checks for Jetson, Pixhawk, Arduino
- jetson/safety_monitor.py - communication checks and emergency land stub
- jetson/file_schema_validator.py - validates GeoJSON and CSV schema
- jetson/hardware_abstraction.py - SerialSprayer and PX4Drone helper classes

Data, analytics, and operations
- jetson/coverage_analyzer.py - creates coverage_report.png from spray_log.csv
- jetson/onboard_data_analysis.py - placeholder mission log summarizer
- jetson/ndvi_bloom_ranker.py - ranks trees by NDVI score
- jetson/report_generator.py - mission_report.pdf from mission.log
- jetson/export_logs.py - CSV and PDF export of mission.log
- jetson/cloud_sync.py - uploads logs to a remote endpoint
- jetson/predictive_maintenance.py - maintenance_state.json and cycle limits
- jetson/smart_alerts.py - SMTP alert sender
- jetson/fleet_manager.py - polls multiple drone APIs for status
- jetson/calibration_tool.py - flow sensor calibration and duration tuning
- jetson/compliance.py - geofence download and placeholder check

Simulation and tests
- jetson/hil_sim.py - simulated mission status for HIL
- jetson/sitl_end_to_end_test.py - PX4 SITL + main_launcher pipeline
- jetson/sawit_test_phase2.py - alternate main_launcher pipeline (Indonesian comments)
- jetson/test_pipeline.py - unit tests for core pipeline
- jetson/test_health_monitor.py - unit test for health_report

Logging
- jetson/logger.py - basic file and console logger
- jetson/log_utils.py - rotating logger helper

### Arduino firmware

- arduino/pwm_sprayer_control.ino - PWM spray command S,<ms> with timeout
- arduino/electrostatic_gimbal_sprayer.ino - PWM spray plus servo gimbal angle A,<deg>
- arduino/sprayer_control_dual_mode.ino - relay or servo mode selectable at runtime
- arduino/sensor_feedback_sprayer.ino - flow sensor feedback and error LED
- arduino/self_test_diagnostics.ino - boot self-test for pins and sensors
- arduino/eeprom_logger.ino - EEPROM logging for spray and error counts

Note: .txt files in arduino/ mirror the .ino sources.

### Pixhawk and mission assets

- pixhawk/drone_sawit.params, pixhawk/*.plan, pixhawk/geofence_polygon.json
- test.plan, test.waypoints, jetson/auto.plan

### Deployment and container

- Dockerfile - Jetson container image (FastAPI backend)
- deployment.sh - builds and runs the container with ports 8000 and 8080

### Data and calibration folders

- data/ - mission logs and reports
- calibration/ - calibration files (imu_calibration.json, sprayer_calibration.yaml, etc.)

### Documentation and notes

- README.md, QUICKSTART.md, ARCHITECTURE.md, API_PROTOCOL.md
- README_DEPLOYMENT.md, README_WIRING_DIAGRAM.md, SAFETY_COMPLIANCE.md
- SIMULATION_GUIDE.md, preflight_checklist.md, hardware.md
- sawit_3.md, sawit_3b.md, Drone sawit 3.txt, Drone sawit 3a.txt, Drone sawit 3b.txt
  These are design notes and draft module breakdowns rather than live code.

### Dependencies

jetson/requirements.txt includes:
- mavsdk, geopy, pandas, pyserial, opencv-python, matplotlib, yaml, scipy
- flask, fastapi, uvicorn, torch, torchvision

### Required files and configuration

You must provide or generate these before running the full pipeline:
- jetson/predicted_trees.geojson - AI detection results (input)
- jetson/pollen_dosage_table.csv - dosage mapping by tree age
- jetson/bloom_model.pt - PyTorch model for BloomClassifier
- jetson/spray_commands_linked.csv - generated by spray_command_mapper

Environment:
- Copy drone_sawit/.env.example to drone_sawit/.env and set weather and cloud keys if used
- Serial ports in code default to /dev/ttyUSB0 (Arduino) and /dev/ttyACM0 (Pixhawk). Adjust if different.
- Add the user to the dialout group for serial access.

### Runbook (minimal -> hardware)

Minimal software check (no hardware):
1) Start the API for smoke test
  python jetson/main.py
2) Use hil_sim to test status endpoint
  python jetson/hil_sim.py

Mission pipeline (with required files):
1) Generate a .plan from AI output
  python jetson/main_launcher.py
2) Upload plan using QGroundControl or upload_plan_mission.py
  python jetson/upload_plan_mission.py route_pollination.plan
3) Start the PX4 spray sync loop
  python jetson/px4_spray_sync.py

Preflight checklist path:
- python jetson/preflight_diagnostics.py
- python jetson/health_monitor.py
- python jetson/compliance.py

### Outputs and logs

- jetson/mission.log - application log (FastAPI, pipeline)
- jetson/drone_sawit.log - logger output
- jetson/spray_log.csv - spray events
- jetson/coverage_report.png - coverage heatmap
- jetson/mission_report.pdf - summary report
- jetson/maintenance_state.json - maintenance cycles

### Testing

- python jetson/test_pipeline.py
- python jetson/test_health_monitor.py
- pytest tests/

### Known gaps and risks

- vision_recheck.py expects inference to return labels and a results object, but ai_inference.py returns only labels.
- auto_mission_planner.py and mission_state_machine.py are placeholders.
- compliance.py uses a stub geofence check.

### If you continue drone_sawit, suggested next tasks

1) Align vision_recheck.py and ai_inference.py return types
2) Replace auto_mission_planner.py with a real planner or connect to palm_planner output
3) Add real geofence point-in-polygon checks in compliance.py
4) Add integration tests for MAVSDK upload and spray sync

## new_plan_2_9 (ROS pollination sprint)

### What this does
ROS-based pollination system built for a 6-day demo sprint. The focus is perception and spray logic with a human pilot in AltHold, then a roadmap to full autonomy with optical flow.

### Architecture modes

Survival mode (current demo path):
- Pilot holds position and approaches manually
- Jetson detects yellow target and triggers spray
- Pixhawk controls fan and feeder via AUX servos

Future full auto mode:
- Optical flow sensor provides position hold
- Jetson visual servoing commands Pixhawk

### Key documents (read in order)

- MASTER_EXECUTION_GUIDE.md - step-by-step setup and daily runbook
- RECOVERY_CHECKPOINT.md - recovery path after ROS reinstall
- ACTION_PLAN_SURVIVAL.md - 6-day sprint plan
- ARCHITECTURE_REVIEW.md - design rationale and feasibility review
- NAVIGATION_ARCHITECTURE.md - future multi-tree navigation FSM
- ADVANCED_SENSOR_FEASIBILITY.md - sensor upgrade analysis
- design_review.md - mechatronics review (encoding appears broken)

### Programs and ROS packages

- src/hil_test.py - HIL test phases (vision, MAVLink, motor response)
- ros_nodes/scripts/detector_node.py - HSV yellow target detector
- ros_nodes/scripts/spray_logic_node.py - spray state machine using mavros
- ros_nodes/scripts/hsv_tuner.py - interactive HSV threshold tuner
- ros_nodes/launch/demo.launch - starts mavros, usb_cam, detector, spray logic
- ros_nodes/msg/Detection.msg - custom ROS message
- quick/opencv_test.py - camera sanity check snippet

### ESP32 firmware (deprecated)

- esp32/sprayer_controller/sprayer_controller.ino - deprecated; architecture moved to Pixhawk servo control

### Configuration

- config/ardupilot_params.param - Pixhawk parameters for optical flow and servo outputs
- requirements.txt - opencv-python, numpy, pymavlink, plus ROS notes

### Runbook

HIL (no ROS):
1) Install deps
  pip install -r requirements.txt
2) Phase 1 detection test
  python src/hil_test.py --phase 1
3) Phase 2 MAVLink test
  python src/hil_test.py --phase 2 --armed --serial /dev/ttyTHS1
4) Phase 3 motor response (secure drone)
  python src/hil_test.py --phase 3 --armed --serial /dev/ttyTHS1

ROS demo:
1) Create catkin workspace and build package (see MASTER_EXECUTION_GUIDE.md)
2) Launch
  roslaunch sprayer_control demo.launch
3) Monitor
  rostopic echo /detection/result
  rostopic echo /spray/status

### Outputs and logs

- ROS topics: /detection/result, /spray/status, /detector/debug_image
- HIL outputs: console logs from hil_test.py

### Known gaps and risks

- design_review.md appears to have encoding issues (garbled text)
- ROS Noetic vs Melodic mismatch across docs; check your Jetson OS version
- Demo assumes manual flight input for positioning in survival mode

### If you continue new_plan_2_9, suggested next tasks

1) Validate the ROS environment in MASTER_EXECUTION_GUIDE.md against your Jetson OS
2) Confirm mavros servo control works end to end (DO_SET_SERVO)
3) Decide whether to stay in survival mode or add optical flow now

## palm_planner (satellite planning web app)

### What this does
Web app to select a region on a map, run palm tree detection, and generate a QGroundControl mission plan. This is the easiest project to run without hardware.

### Components

Backend (Flask):
- backend/app.py - dummy detector, creates visualization and a simple QGC plan
- backend/app_roboflow_workflow.py - main backend with multiple detector options and model switching
- backend/palm_tree_detector.py - YOLO-based detector with fallback images
- backend/roboflow_workflow.py - Roboflow workflow detector via inference-sdk
- backend/roboflow_integration.py - Roboflow local model integration with fallback
- backend/test_api_roboflow.py - Roboflow API test script
- backend/utils/geo_utils.py - haversine distance and area utilities
- backend/models/dummy_detector.py - empty placeholder
- backend/requirements.txt - Flask, torch, opencv, ultralytics, inference-sdk, etc.
- backend/README_test.md - PowerShell testing examples for /health and /process_region

Frontend (React + Leaflet):
- frontend/src/App.js - map UI, area selection, model switch, calls backend /process_region
- frontend/src/index.js - React entry point
- frontend/src/reportWebVitals.js - CRA performance hook
- frontend/src/setupTests.js - jest-dom setup
- frontend/src/App.test.js - default CRA test
- frontend/package.json - React scripts, Leaflet, Tailwind dev deps
- frontend/README.md - Create React App usage

Dataset tooling:
- organize_dataset.py - builds YOLO-style dataset folders and palm_trees.yaml
- backend/datasets/ - datasets and labels (not application code)

Project package.json:
- palm_planner/package.json exists but is empty ({}).

### Runbook

Backend (dummy or Roboflow):
1) Install deps
  pip install -r backend/requirements.txt
2) Start dummy backend
  python backend/app.py
3) Or start Roboflow workflow backend
  python backend/app_roboflow_workflow.py

Frontend:
1) Install deps
  cd frontend && npm install
2) Start dev server
  npm start

Optional Roboflow settings:
- Set ROBOFLOW_API_KEY in your environment for workflow mode

### Outputs

- JSON response with detections, statistics, and mission plan
- Base64 visualization image (returned by backend)
- Generated QGC plan content (in API response)

### Known gaps and risks

- app.py uses a dummy detector that generates random trees
- Roboflow workflow depends on external API availability
- palm_planner/package.json is empty and unused

### If you continue palm_planner, suggested next tasks

1) Decide whether to use local YOLO or Roboflow workflow as the primary detector
2) Standardize the plan output format and integrate with drone_sawit pipeline
3) Add tests for the /process_region endpoint

## mekanik (mechanical CAD assets)

### What this does
Mechanical designs for sprayer, auger, and drone components. This folder contains CAD and model snapshots only.

### File types
- .SLDASM, .SLDPRT - SolidWorks assemblies and parts
- .STEP, .f3d - exchange and Fusion 360 models
- snapshot folders - CAD previews and intermediate data

### How to use
- Open the SolidWorks files with SolidWorks
- Open .f3d in Fusion 360
- Use .STEP for CAD interchange

## Known gaps and placeholders (global)

- Some modules are stubs or placeholders (auto_mission_planner.py, mission_state_machine.py, onboard_data_analysis.py, compliance.py).
- vision_recheck.py expects BloomClassifier.infer to return labels and results, but ai_inference.py returns only labels.
- design_review.md appears to be encoded with a non-UTF8 character set (garbled characters in headings).

## Quick reference commands

Drone Sawit
- Preflight: python jetson/preflight_diagnostics.py
- Backend: python jetson/main.py
- Dashboard: http://<jetson-ip>:8000/mission_dashboard.html

new_plan_2_9
- HIL test: python src/hil_test.py --phase 1
- ROS demo: roslaunch sprayer_control demo.launch

palm_planner
- Backend: python backend/app.py (or app_roboflow_workflow.py)
- Frontend: npm start in frontend/
