import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

class CsiCameraNode(Node):
    def __init__(self):
        super().__init__('csi_camera_node')
        
        # Declare parameters
        self.declare_parameter('camera_id', 0)
        self.declare_parameter('width', 640)  # Default to 640
        self.declare_parameter('height', 480) # Default to 480
        self.declare_parameter('framerate', 30.0)
        self.declare_parameter('flip_method', 0)
        self.declare_parameter('topic_name', '/camera/image_raw')
        
        # NEW: Declare camera type parameter
        self.declare_parameter('camera_type', 'jetson') # 'jetson' or 'rpi'
        
        # Get parameters
        camera_id = self.get_parameter('camera_id').value
        width = self.get_parameter('width').value
        height = self.get_parameter('height').value
        framerate = self.get_parameter('framerate').value
        flip_method = self.get_parameter('flip_method').value
        topic_name = self.get_parameter('topic_name').value
        camera_type = self.get_parameter('camera_type').value # Get the new param

        self.bridge = CvBridge()

        # DYNAMICALLY BUILD PIPELINE BASED ON PARAMETER
        if camera_type == 'rpi':
            self.get_logger().info("Configuring for Raspberry Pi (libcamera)...")
            # Note: If you use a camera other than V2 (IMX219), you may need to 
            # change the 'camera-name' path in this pipeline.
            gst_pipeline = (
                f"libcamerasrc camera-name=/base/soc/i2c0mux/i2c@1/imx219@10 ! "
                f"video/x-raw,width={width},height={height},framerate={framerate}/1 ! "
                f"videoconvert ! "
                f"video/x-raw,format=BGR ! "
                f"appsink"
            )
        else: # Default to Jetson
            self.get_logger().info("Configuring for NVIDIA Jetson (nvargus)...")
            gst_pipeline = (
                f"nvarguscamerasrc sensor-id={camera_id} ! "
                f"video/x-raw(memory:NVMM), width={width}, height={height}, framerate={framerate}/1 ! "
                f"nvvidconv flip-method={flip_method} ! "
                f"video/x-raw, format=BGRx ! "
                f"videoconvert ! "
                f"video/x-raw, format=BGR ! "
                f"appsink"
            )

        self.get_logger().info(f"Opening CSI camera with pipeline:\n{gst_pipeline}")
        self.cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

        if not self.cap.isOpened():
            self.get_logger().error("Failed to open CSI camera. Check your GStreamer pipeline.")
            raise RuntimeError("Could not initialize camera.")

        # Create publisher
        self.publisher_ = self.create_publisher(Image, topic_name, 10)
        self.get_logger().info(f"Publishing to {topic_name}")

        # Create timer to capture and publish frames
        timer_period = 1.0 / framerate
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        ret, frame = self.cap.read()
        
        if ret:
            # Convert OpenCV image to ROS Image message
            try:
                ros_image = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
                ros_image.header.stamp = self.get_clock().now().to_msg()
                ros_image.header.frame_id = "camera_link"
                self.publisher_.publish(ros_image)
            except Exception as e:
                self.get_logger().error(f"Failed to convert and publish image: {e}")
        else:
            self.get_logger().warning("Failed to read frame from camera.")

    def destroy_node(self):
        self.get_logger().info("Shutting down camera...")
        if self.cap.isOpened():
            self.cap.release()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = CsiCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()