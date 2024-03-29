import cv2, dlib
import numpy as np
import math, sys
import matplotlib.pyplot as plt
import matplotlib

# Function to calculate the intereye distance.
def interEyeDistance(predict):
  leftEyeLeftCorner = (predict[36].x, predict[36].y)
  rightEyeRightCorner = (predict[45].x, predict[45].y)
  distance = cv2.norm(np.array(rightEyeRightCorner) - np.array(leftEyeLeftCorner))
  distance = int(distance)
  return distance

def align_video(video_path, predictor_path, out_path, showStabilized = False):
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    writer = cv2.VideoWriter(out_path, fourcc, 20, (640,480), True)

    # Initializing video capture object.
    cap = cv2.VideoCapture(videoFileName)

    if(cap.isOpened()==False):
      print("Unable to load video")

    winSize = 101
    maxLevel = 10
    fps = 30.0
    # Grab a frame
    ret,imPrev = cap.read()

    size = imPrev.shape[0:1]

    detector = dlib.get_frontal_face_detector()
    landmarkDetector = dlib.shape_predictor(predictor_path)
    # Initializing the parameters
    points=[]
    pointsPrev=[]
    pointsDetectedCur=[]
    pointsDetectedPrev=[]

    eyeDistanceNotCalculated = True
    eyeDistance = 0
    isFirstFrame = True
    # Initial value, actual value calculated after 100 frames
    fps = 10
    count =0


    ret, frame1 = cap.read()
    imGrayPrev = cv2.cvtColor(frame1,cv2.COLOR_BGR2GRAY)

    try:
        while(True):
            if (count==0):
                t = cv2.getTickCount()
            # Grab a frame
            ret,im = cap.read()
            if im is None:
                break
            imDlib = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            # COnverting to grayscale
            imGray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
            height = im.shape[0]
            IMAGE_RESIZE = float(height)/RESIZE_HEIGHT
            # Resize image for faster face detection
            imSmall = cv2.resize(im, None, fx=1.0/IMAGE_RESIZE, fy=1.0/IMAGE_RESIZE,interpolation = cv2.INTER_LINEAR)
            imSmallDlib = cv2.cvtColor(imSmall, cv2.COLOR_BGR2RGB)
            # Skipping the frames for faster processing
            if (count % SKIP_FRAMES == 0):
                faces = detector(imSmallDlib,0)
            # If no face was detected
            if len(faces)==0:
                print("No face detected")
            # If faces are detected, iterate through each image and detect landmark points
            else:
                for i in range(0,len(faces)):
                # Face detector was found over a smaller image.
                # So, we scale face rectangle to correct size.
                newRect = dlib.rectangle(int(faces[i].left() * IMAGE_RESIZE),
                    int(faces[i].top() * IMAGE_RESIZE),
                    int(faces[i].right() * IMAGE_RESIZE),
                    int(faces[i].bottom() * IMAGE_RESIZE))
                
                # Detect landmarks in current frame
                landmarks = landmarkDetector(imDlib, newRect).parts()
                
                # Handling the first frame of video differently,for the first frame copy the current frame points
                
                if (isFirstFrame==True):
                    pointsPrev=[]
                    pointsDetectedPrev = []
                    [pointsPrev.append((p.x, p.y)) for p in landmarks]
                    [pointsDetectedPrev.append((p.x, p.y)) for p in landmarks]
                # If not the first frame, copy points from previous frame.
                else:
                    pointsPrev=[]
                    pointsDetectedPrev = []
                    pointsPrev = points
                    pointsDetectedPrev = pointsDetectedCur
                # pointsDetectedCur stores results returned by the facial landmark detector
                # points stores the stabilized landmark points
                points = []
                pointsDetectedCur = []
                [points.append((p.x, p.y)) for p in landmarks]
                [pointsDetectedCur.append((p.x, p.y)) for p in landmarks]
                # Convert to numpy float array
                pointsArr = np.array(points,np.float32)
                pointsPrevArr = np.array(pointsPrev,np.float32)
                # If eye distance is not calculated before
                if eyeDistanceNotCalculated:
                    eyeDistance = interEyeDistance(landmarks)
                    print(eyeDistance)
                    eyeDistanceNotCalculated = False
                if eyeDistance > 100:
                    dotRadius = 3
                else:
                    dotRadius = 2
                sigma = eyeDistance * eyeDistance / 400
                s = 2*int(eyeDistance/4)+1
                #  Set up optical flow params
                lk_params = dict(winSize  = (s, s), maxLevel = 5, criteria = (cv2.TERM_CRITERIA_COUNT | cv2.TERM_CRITERIA_EPS, 20, 0.03))
                # Python Bug. Calculating pyramids and then calculating optical flow results in an error. So directly images are used.
                # ret, imGrayPyr= cv2.buildOpticalFlowPyramid(imGray, (winSize,winSize), maxLevel)
                pointsArr,status, err = cv2.calcOpticalFlowPyrLK(imGrayPrev,imGray,pointsPrevArr,pointsArr,**lk_params)
                
                # Converting to float
                pointsArrFloat = np.array(pointsArr,np.float32)
                # Converting back to list
                points = pointsArrFloat.tolist()
                # Final landmark points are a weighted average of
                # detected landmarks and tracked landmarks
                for k in range(0,len(landmarks)):
                    d = cv2.norm(np.array(pointsDetectedPrev[k]) - np.array(pointsDetectedCur[k]))
                    alpha = math.exp(-d*d/sigma)
                    points[k] = (1 - alpha) * np.array(pointsDetectedCur[k]) + alpha * np.array(points[k])
                # Drawing over the stabilized landmark points
                if showStabilized is True:
                    for p in points:
                    cv2.circle(im,(int(p[0]),int(p[1])),dotRadius, (255,0,0),-1)
                else:
                    for p in pointsDetectedCur:
                    cv2.circle(im,(int(p[0]),int(p[1])),dotRadius, (0,0,255),-1)
                isFirstFrame = False
                count = count+1
                # Calculating the fps value
                if ( count == NUM_FRAMES_FOR_FPS):
                    t = (cv2.getTickCount()-t)/cv2.getTickFrequency()
                    fps = NUM_FRAMES_FOR_FPS/t
                    count = 0
                    isFirstFrame = True
                # Display the landmarks points
                cv2.putText(im, "{:.1f}-fps".format(fps), (50, size[0]-50), cv2.FONT_HERSHEY_COMPLEX, 1.5, (0, 0, 255), 3,cv2.LINE_AA)
                winName = "Aligned facial landmark detector"
                cv2.imshow(winName, im)
                frame_1 = cv2.resize(im,(640,480)) # manually resize frame
                writer.write(frame_1)
                key = cv2.waitKey(25) & 0xFF
                # Use spacebar to toggle between Stabilized and Unstabilized version.
                if key==32:
                    showStabilized = not showStabilized
                # Stop the program.
                if key==27:
                    sys.exit()
                # Getting ready for next frame
                imPrev = im
                imGrayPrev = imGray
    except Exception as e:
        print("Exceptions occurs......")
        writer.release()
        cap.release()
        cv2.destroyAllwindows()

if __name__ == "__main__":
    matplotlib.rcParams['figure.figsize'] = (6.0,6.0)
    matplotlib.rcParams['image.cmap'] = 'gray'
    PREDICTOR_PATH_5 =  "/home/krishnanand/Videos/Webcam/shape_predictor_5_face_landmarks.dat"
    PREDICTOR_PATH_68 =  "/home/krishnanand/Videos/Webcam/shape_predictor_68_face_landmarks.dat"

    RESIZE_HEIGHT = 480
    NUM_FRAMES_FOR_FPS = 100
    SKIP_FRAMES = 4

    videoFileName = "/home/krishnanand/Videos/Webcam/original.ogv"
    five_point_aligned_video = "/home/krishnanand/Videos/Webcam/5point_aligned.mov"
    unstabilised_points_video = "/home/krishnanand/Videos/Webcam/unstabilised.mov"
    stabilised_points_video = "/home/krishnanand/Videos/Webcam/stabilised.mov"
    
    align_video(videoFileName, PREDICTOR_PATH_5, five_point_aligned_video)
    align_video(five_point_aligned_video, PREDICTOR_PATH_68, unstabilised_points_video)
    align_video(five_point_aligned_video, PREDICTOR_PATH_68, stabilised_points_video, showStabilized = True)
