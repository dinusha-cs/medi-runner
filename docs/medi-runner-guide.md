Medi-Runner Challenge 2026 
Stage-by-Stage Guide 
 
 
“In a hospital where every second matters and every patient counts, a new assistant is 
being born. A robot designed to lighten workloads, support caregivers, and move with 
purpose through the hospital’s daily rhythm. Today, you guide its first steps.” 
 
 
Each stage advances the story of a hospital delivery robot evolving from a basic prototype 
to an intelligent medical supply runner that understands signs, zones, and missions. 
Each stage contains two parallel tracks: 
•          Robotics Track – physical build, sensors, motors, camera, handle autonomous 
operations (Pilot and sub-team are responsible for handling this track). 
•        Software Track – Control system, AI, streaming, mission UI, handle 
manual operations (Co-pilot and sub-team are responsible for handling this track). 
Team members must handle both tracks simultaneously. 
 
Given the limited time window to build this working POC, it’s essential to strategically plan 
your mission based on the priority and weight of each feature—while also accounting for 
penalties, time constraints, and time-related risks. With this in mind, each team’s 
Innovation Lead can closely monitor progress, ensure strategic alignment, and guide the 
team toward success. At the same time, innovation leads can begin sketching out ideas for 
more advanced and innovative extensions to be tackled in the final stage (Stage 4) of the 
competition. 
 
 
 
 
 STAGE 1 — Birth of the Medi-Runner  
 
“Every hospital robot begins as a simple frame and a handful of wires… and a spark of 
hope.” 
 
This stage establishes the foundation of the Medi-Runner.  
 
  Robotics Track: 
 
1. Assemble the robot 
• Assemble the car kit (chassis, wheels, motors, etc.) 
according to the instruction manual that comes with  
the car kit itself: 
 
Special notes:  
 - Please ignore the switch placement in Step 1 since we  
   are providing you with a separate sophisticated power supply  
   with a switch.  
 - Also ignore step 4 as well, given that the above mentioned 
  power supply comes with pair of batteries.  
 - We recommend you consider the side that caster wheel is fixed as the rear side of 
the vehicle.  
 
2. Connect electronic components 
 
• Then fix the power supply, motor controller, Raspberry PI. If you fix the power supply 
at the very back of the car kit, that would be helpful for gaining a good weight balance 
throughout the whole cat kit. You can use a few small segments of  double tapes or 
available nuts and bolts to fix them for the car as you wish.  
Raspberry PI should be plugged into the power supply only using the USB to mini
USB cable that is provided. Do not try to power PI using GPIO pins. 
 
• Also fix the cam module (Be careful here since the wire strip can be damaged if you 
try to do this forcefully). [TIP: You can take AI assistance]  
 
• Then fix the IR array using given spacer to the front side of the car. (Even though you 
fix it this would come into the competition in the next stage. So don’t worry that much 
about program level integration yet, only the physical presence and wiring would be 
enough)  
 
 
 
 
 
 
 
 
 
 
 
 
 
 
• For all the pin and wiring diagrams please see the Appendix at the end of this 
document. Given wiring diagrams are provided as examples and not 100% optimized 
for wiring neatness, etc.  You can always choose not to go ahead with that if you need 
to achieve a greater wring neatness and if you have enough confidence in what you 
are really doing. 
 
3. What you’ll need to show at the end to prove you have a working robot that is ready to 
be fully grown in the next stages: 
•  A simple program to drive the robot 2 seconds forward → stop for 1 second → turn right 
and drive for 2 more seconds → stop for 1 second → turn left and drive for 2 more 
seconds → stop and take a snapshot and save it → drive backwards for 2 seconds → 
stop. 
[Note that this doesn’t include any line following aspect yet, this is purely to test the 
robot is working as expected in its very early stages.] 
 
4. What you’ll be evaluated against: 
• Wiring neatness. 
• Proper execution of above-mentioned final action sequence.  
 
  Software Track:  
 
As the robot begins its first movements, a control panel and a dashboard that hospital staff 
will rely on also should be built. This app will become the window into the robot’s status, 
movements, tasks etc. 
1. Building the entrance phase of the application  
• A web application should be created aiming to have a control panel and a 
dashboard for the robot so that hospital staff can see what’s going on with robot and 
to control it whenever needed. ( In current stage, there is no need to implement those 
actuals) 
• For this stage what you need to concentrate on is login and navigation. 
 
(i) You need to implement login mechanism using face recognition. So, there should 
be a way to enroll the users in the system, and a way to authenticate users based on 
those enrolments and should allow or deny users entering to the system based on 
that. A futuristic/ modernistic UI/UX  will be expected here. 
 
(ii) You need to implement Voice  navigation/ assistance to this enrollment and 
logging process.  
 
e.g.: A user says “enroll me” → application responds, “Alright taking you to face 
enrollment section” → “Opening camera” → “Please focus on middle area of the 
screen” → “ Okays successfully enrolled the face”. 
 
Add your creativity for this so that both UI and UX align with the end goal, which is to 
provide a more modernistic/futuristic feeling for the hospital staff.  
 
2. What you’ll need to showcase: 
• User enrollment. 
• User recognition and allowing/disallowing them to enter the application. 
• Same above functionality with Voice navigation/assist (you may have a simple 
switch to enable/disable voice assist) 
 
3. What you’ll be evaluated against: 
• Face recognition confusion matrix. 
• Face recognition futuristic UI/UX. 
• Voice navigation/assist UX. 
• Creativity. 
 
 
 
 
 
 
 
 
 
 
 
 
 
 STAGE 2 — Explore Hospital Corridor Logistic Paths 
 
“A Medi-Runner must master the colored logistic paths that are marked on the hospital 
floor.” 
 
   Robotics Track:  
 
1. Calibrate the 5-way tracking sensor. 
• Black line = 0 
• White floor = 1 
 
2. Teach your robot to follow different corridor path patterns 
Practice on the training tracks that you have : 
• Straight path 
• Smooth curve path 
• Circular loop path 
• Rectangular loop path 
• Zig-zag path 
You can only use your team specific arena to practice; main arena can’t be used for 
practice purposes. 
 
3. What you’ll need to showcase: 
• Let your robot move on above paths in autonomous mode (in your team arena). 
• Let your robot complete a full round in main arena in autonomous mode.   
 
 
4. What you’ll be evaluated against: 
• How smooth can your robot move on above paths (in your team arena). 
• How successful, how fast and how smooth your robot can complete a full round in 
main arena.  
 
 
   Software Track:  
 
“Nurses and technicians should be able to tele-drive robots in special situations. So, a 
control panel is a necessity for the app.” 
Now users can sign in to your application and there should be a dashboard to see all the real 
time data (But let’s go there in the next step. In this step you are going to build the control 
panel, as it is the next in the priority list). [Also no need of voice assist to be continued here 
onwards.] 
 
So, in your control panel, 
1. Add an option to switch robot mode, between manual and autonomous. 
• So once set to autonomous mode, robot should handle everything on its own.  
And in manual mode there are specific set of requirements as in described 
shortly.  
2. In both modes, users should be able to see a real-time video stream from the robot. 
3.  In manual mode, there should be a virtual controller for control forward, backward, 
left, right movements and the stop. 
• The virtual controller is expected to offer seamless, highly refined user experience 
in all respects. Basically, this functionality and real time video streaming 
functionality should create a real tele-drive experience for the user. 
4. In manual mode there should be a 360° panoramic scan option. 
• When a user tele-drive the robot, if he/she needs to take a full 360° panoramic 
image of a particular location, user should be able to simply press a button and 
do that. So, when user presses the button, robot should take the 360° image and 
send it back to the application and application should be able to show case the 
image in a 360° image viewer. 
5. What you’ll need to showcase: 
• All the above functionalities.  
 
6. What you’ll be evaluated against: 
• Functionality completeness (as obvious) 
• UI 
• UX as in UX in your app  + UX when controlling robot using your virtual controller. 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
STAGE 3 — Understanding Hospital Signs & Zones 
 
“Now the Medi-Runner must read the walls, understand the signs, and navigate like a 
true hospital assistant.” 
 
  Robotics Track: 
 
Hospital hallways typically use: 
• Color-coded zones 
• Directional signs for departments 
Your robot must decode them. 
 
1.  Zone Identification (Color Detection) 
Each hospital zone has meaning. So, it is important to understand them by your robot. 
 
Color Realistic Hospital Meaning Robot Behavior 
  Blue Imaging, diagnostics 1 beep + continue 
  Red Emergency, critical zone 2 quick beeps + continue 
  Green General area 3 quick beeps + continue 
  Yellow Caution / transitions 4 quick beeps + continue 
 
2. Hospital direction boards (Signboard Detection) 
Examples: 
• X-ray → 
• MRI ← 
• Emergency 
• ICU ↑ 
Robot must: 
• Read sign text 
• Interpret arrow 
• Move accordingly 
• Beep at destination  
 
3. What you’ll need to showcase: 
• Zone detections indications with given no. of beeps.  
• Find the given unit and emit 5 consecutive beeps (unit will be given right before 
demo – so you can either have a place holder to replace the unit name and 
quickly update the python program right before your turn or else you can have 
some simple place in your software’s autonomous mode related area to send 
the unit that robot needs to find. ). 
 
4. What you’ll be evaluated against: 
• Working functionality. 
 
  Software track:  
 
Alright now it is time to come to the dashboard functionality. 
 
1. Show real time information  
• Display real time information including zone status (which color zone robot is 
currently in), mode (autonomous or manual), power supply voltage, relative 
speed. 
 
2. A prompt-based mission accomplishment system 
• Users can enter commands in natural language (as the first step let’s consider 
English as the natural language) like: 
       “I want to deliver ‘XYZ’ From X-ray to MRI. Then deliver “PQRS” from MRI to ICU.” 
So, robot must: 
• Follow signboards and navigate to each pickup and destination point in 
the correct order. Can indicate a pickup point by a single beep whereas a 
destination point from 2 consecutive beeps.   
 
3. A live logical Mini-Map. 
• Using: Line following data, Detected marks and Junction decisions. 
• Teams must display: A small 2D graph-based path trace with zones visited, stops 
and beeps (to track mission wise history using a visual representation). 
 
4. What you’ll need to showcase: 
•  Dashboard with real time data while robot moves. 
•  Successful robot navigation when a prompt is provided. 
•  The logical mini map. 
 
5. What you’ll be evaluated against: 
•  Working functionality. 
•  UI/UX 
 
 
 
 
 
  STAGE 4 — The Future of Medical Logistics 
 
“The Medi-Runner must now evolve beyond the rules, beyond the fixed track… into a 
true hospital asset.” 
 
This is a very open-ended competition stage and you should extend the current Medi runner 
robot with any great idea that you have to brighten the future of medical logistics. No need 
to be only concerned on logistics side, you can extend this with any fabulous idea as a multi
functional hospital assistant robot. [TIP: You can always get the help of AI deep search tools 
here] 
If you have a great idea and if there are any barriers such as lack of needed electronic sensors 
and stuff or lack of time to fully implement the solution, you can always present a solid POC 
with a fair enough root. What matters most in this stage is the best idea! 
 
1. What you’ll need to showcase: 
At the end of this stage, you need to present the whole system that you have built so far 
and your innovative extension. 
So, in final demo you will get 10 minutes to present it all. And the presentation should cover 
a quick demo recap on the areas below while mainly focusing on your innovative idea.  
• Face enrollment + recognition with voice assist. 
• Auto and manual modes. 
• Real time video streaming + virtual robot controller for manual mode 
• 360 panoramic view capture and view it in web app. 
• Dashboard with live information 
• Prompt navigation 
 
2. What you’ll be evaluated against: 
• Overall functional completeness level. 
• Overall UI/UX. 
• Superiority of your innovative extension. 
 - End of the guide - 
         Appendix 
 
Electronic items you’ll be using today. 
• Raspberry PI 4 8GB Ram board 
 
 
 
 
• TCRT5000 5 Channel 5-Way IR Obstacle Avoidance Sensor Module 
 
 
• L298N motor driver 
 
 
 
 
• LM2596 DC-DC buck converter 
 
 
• 5V active buzzer 
 
• Camera V1.3 5MP 
 
Power pack composition  
(two 8650 pink 3200MAH flat top batteries with battery holder + buck convertor+ female 
USB slot+ switch) 
 
 
 
 
 
 
 
 
 
 
How to connect the L298N Motor Driver and motors to the Raspberry Pi. 
 
 
 
 
            
    
 
 
                *ppn = physical pin number 
 
https://app.cirkitdesigner.com/project/aed93caa-ad7d-460e-ac9a-121efaa313e6 
 
 
 
Raspberry pi Motor Controller 
GPIO20 [ppn = 38] ENA 
GPIO23 [ppn = 16] IN1 
GPIO22 [ppn = 15] IN2 
GPIO27 [ppn = 13] IN3 
GPIO17 [ppn = 11] IN4 
GPIO16 [ppn = 36] ENB 
How to connect 5-way IR array 
 
 
 
Rasbery pi  IR array 
5V [ppn = 4] 5V 
GND [ppn = 6] GND 
GPIO5 [ppn = 29] S1 
GPIO6 [ppn = 31] S2 
GPIO13 [ppn = 33] S3 
GPIO19 [ppn = 35] S4 
GPIO26 [ppn = 37] S5 
              *ppn = physical pin number 
 
https://app.cirkitdesigner.com/project/aed93caa-ad7d-460e-ac9a-121efaa313e6 
 
How to connect camera and active buzzer 
 
 
 
Rasbery pi Camera 
Camera slot Camera ribbon 
            
Rasbery pi Buzzer 
GND [ppn = 6] GND 
GPIO24 [ppn = 18] VCC 
              
            *ppn = physical pin number 
 
 
https://app.cirkitdesigner.com/project/aed93caa-ad7d-460e-ac9a-121efaa313e6 
 
 
 
Overall wiring diagram  
 
 
 
 
  
 
https://app.cirkitdesigner.com/project/aed93caa-ad7d-460e-ac9a-121efaa313e6 
 