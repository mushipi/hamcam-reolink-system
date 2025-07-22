# RLC-510A Camera System with Hamster Tracking

A comprehensive camera monitoring system for RLC-510A with advanced hamster behavioral analysis and DeepLabCut integration.

## 🌟 Features

### Phase 1 & 2: Core Camera System
- **RTSP Streaming**: Real-time video stream processing
- **API Integration**: Complete Reolink camera API support
- **Lighting Detection**: Automatic day/night mode detection
- **Recording & Snapshots**: Automated media capture

### Phase 3: Advanced Hamster Tracking System
- **Automated Data Collection**: Scheduled and motion-triggered image capture
- **High-Precision Motion Detection**: Hamster-specific movement analysis
- **Coordinate Calibration**: Pixel-to-mm conversion for accurate measurements
- **Data Quality Assessment**: Multi-metric image quality evaluation
- **DeepLabCut Integration**: Optimized data collection for machine learning

## 🎯 System Specifications

### Hardware Requirements
- **Camera**: Reolink RLC-510A (or compatible)
- **Resolution**: 480×640 (sub-stream) / 1920×1080 (main-stream)
- **Network**: Ethernet/WiFi connection to camera
- **Cage**: 380×280mm (standard), customizable

### Software Requirements
- Python 3.8+
- OpenCV 4.5+
- NumPy, PyYAML
- Anaconda (recommended)

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/mushipi/hamcam-reolink-system.git
cd hamcam-reolink-system
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your camera settings
```

### 3. Camera Setup
- Connect RLC-510A to your network
- Configure camera IP and credentials in `.env`
- Test connection: `python basic_connection_test.py`

### 4. Coordinate Calibration
```bash
# Run GUI calibration tool
./run_calibration_gui.sh
# Or Windows: run_calibration_gui.bat
```

### 5. Start Hamster Tracking System
```bash
# Full system with GUI
python auto_capture_main.py

# Test mode (1 minute)
python auto_capture_main.py --test --duration 60

# Manual capture test
python auto_capture_main.py --manual-trigger
```

## 📁 Project Structure

```
hamcam-reolink-system/
├── 📄 README.md                     # This file
├── 📄 requirements.txt              # Python dependencies
├── 📄 .env.example                  # Configuration template
├── 📂 phase3_hamster_tracking/      # Main tracking system
│   ├── 📄 README.md                 # System overview
│   ├── 📂 config/                   # Configuration files
│   ├── 📂 data_collection/          # Core collection modules
│   ├── 📂 hamster_tracking/         # Tracking algorithms
│   ├── 📂 utils/                    # Utility modules
│   └── 📂 docs/                     # Technical specifications
├── 📂 examples/                     # Usage examples
├── 📂 utils/                        # Shared utilities
└── 📂 docs/                         # Project documentation
```

## 🎮 Usage Examples

### Basic Camera Operations
```python
from rtsp_stream import RTSPStream

# Initialize stream
stream = RTSPStream(stream_type='sub')
stream.start_stream()

# Capture frame
success, frame = stream.get_frame()
if success:
    # Process frame
    pass

stream.stop_stream()
```

### Hamster Tracking System
```python
from phase3_hamster_tracking.data_collection.auto_capture_system import AutoCaptureSystem
from phase3_hamster_tracking.utils.hamster_config import load_config

# Load configuration
config = load_config()

# Initialize system
capture_system = AutoCaptureSystem(config)

# Start automated capture
capture_system.start()

# System runs continuously until stopped
# capture_system.stop()
```

### Motion Detection
```python
from phase3_hamster_tracking.data_collection.motion_detector import MotionDetector

detector = MotionDetector(config)

# Detect motion in frame
motion_events = detector.detect_motion(frame)

for event in motion_events:
    print(f"Motion detected at {event.center} with confidence {event.confidence}")
```

## 🔧 Configuration

### Camera Settings (`.env`)
```bash
CAMERA_IP=192.168.1.100
CAMERA_USERNAME=admin
CAMERA_PASSWORD=your_password
```

### System Configuration (`hamster_config.yaml`)
```yaml
cage:
  width: 380.0    # mm
  height: 280.0   # mm

quality_assessment:
  enabled: true
  min_confidence_ratio: 0.8

data_collection:
  storage:
    base_directory: "./data"
    max_storage_days: 7
```

## 📊 Performance Metrics

- **Capture Success Rate**: 98%+
- **Motion Detection Accuracy**: 95%+
- **Processing Speed**: ~14.5fps real-time
- **Coordinate Precision**: ±1mm accuracy
- **Data Quality**: Multi-metric assessment (blur, brightness, contrast, noise)

## 🧪 Testing & Validation

### System Tests
```bash
# Camera connection test
python test_camera_connection.py

# Basic functionality test
python test_basic_functionality.py

# Lighting detection test
python test_lighting_manual.py

# Full system test (1 minute)
python auto_capture_main.py --test --duration 60
```

### Data Quality Validation
- **Blur Detection**: Laplacian variance analysis
- **Brightness Assessment**: Optimal range evaluation
- **Hamster Visibility**: Automated presence detection
- **DeepLabCut Suitability**: Learning data quality scoring

## 🤖 DeepLabCut Integration

The system is optimized for DeepLabCut training data collection:

1. **High-Quality Filtering**: Automatic quality assessment
2. **Pose Variety**: Motion-triggered capture ensures diverse poses
3. **Metadata Rich**: Detailed capture conditions and quality metrics
4. **Coordinate Mapping**: Real-world measurements for accurate training

### Recommended DeepLabCut Workflow
1. Collect 200-500 high-quality images using this system
2. Use coordinate calibration for accurate landmark positioning
3. Train DeepLabCut model with collected dataset
4. Integrate trained model back into motion detection pipeline

## 🛠 Development & Customization

### Adding New Cage Sizes
```yaml
# config/cage_profiles/custom_cage.yaml
cage:
  width: 450.0    # Your cage width in mm
  height: 320.0   # Your cage height in mm
```

### Custom Motion Detection
```python
class CustomMotionDetector(MotionDetector):
    def _filter_hamster_contours(self, contours):
        # Implement custom filtering logic
        return filtered_contours
```

### Quality Assessment Customization
```python
class CustomQualityAssessor(DataQualityAssessor):
    def evaluate_custom_metric(self, image):
        # Implement custom quality metrics
        return score
```

## 📚 Documentation

- **[System Overview](phase3_hamster_tracking/README.md)**: Complete system documentation
- **[Auto Capture System](phase3_hamster_tracking/docs/auto_capture_system.md)**: Automated data collection
- **[Motion Detection](phase3_hamster_tracking/docs/motion_detection_system.md)**: Advanced movement analysis
- **[Coordinate Calibration](phase3_hamster_tracking/docs/coordinate_calibration_system.md)**: Precision measurement system
- **[Data Quality Assessment](phase3_hamster_tracking/docs/data_quality_assessment_system.md)**: Quality evaluation system

## 🐛 Troubleshooting

### Common Issues

#### Camera Connection Failed
- Check camera IP address and network connectivity
- Verify credentials in `.env` file
- Ensure camera is powered on and accessible

#### Poor Motion Detection
- Recalibrate coordinate system using GUI tool
- Adjust motion detection sensitivity in config
- Check lighting conditions (infrared mode recommended)

#### Low Image Quality Scores
- Improve lighting conditions
- Clean camera lens
- Adjust quality thresholds in configuration

### Debug Commands
```bash
# Enable verbose logging
python auto_capture_main.py --verbose

# Test specific components
python -m phase3_hamster_tracking.tests.test_lighting_detection

# Manual calibration check
python test_calibration_gui_offline.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Commit: `git commit -am 'Add feature'`
5. Push: `git push origin feature-name`
6. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Reolink**: For excellent camera hardware and API documentation
- **DeepLabCut**: For the amazing pose estimation framework
- **OpenCV Community**: For robust computer vision tools
- **Python Ecosystem**: For the incredible libraries that make this possible

---

## 📈 Project Status

- ✅ **Phase 1**: Basic camera connection and API integration
- ✅ **Phase 2**: RTSP streaming and lighting detection
- ✅ **Phase 3**: Complete hamster tracking and data collection system
- 🔄 **Future**: DeepLabCut model integration and real-time behavioral analysis

**Current Version**: v1.0 - Production Ready

For questions, issues, or contributions, please open an issue on GitHub!

---

*Built with ❤️ for advancing animal behavioral research*
