# EduMate Kids: school setup and videos

EduMate Kids is a teacher-guided preschool area with four ungraded demonstration activities. The activities are examples, not reviewed curriculum, and are not saved to pupil progress. Teachers and school leaders must review material for age suitability before real use.

## Prepare a school
1. A school administrator adds Nursery, KG 1 and KG 2 in School setup, sets up desired subjects and assigns teachers to their classes and subjects. These are school-defined settings, not automatically created for existing schools.
2. Register learners and enrol them in the correct class. A teacher creates and publishes a lesson for that class.
3. In My Lessons, open the lesson. Upload a school-owned or appropriately licensed MP4 (up to 50 MB), or add a YouTube watch link for online use. Only upload material the school is permitted to use.
4. An uploaded video or new YouTube link resets the lesson to pending review. A school administrator checks the material and marks the lesson reviewed in Curriculum & educator review. Only then can learners see the video. This review is a school record, not NaCCA approval. Changes to a video require another review.
5. A learner opens EduMate Kids and selects a preschool lesson. An adult should assist young children. Videos and YouTube embeds need an internet connection unless an uploaded MP4 was saved for offline use.

## Offline
While online, the student opens the reviewed lesson and selects Save for offline reading. The app downloads its available attachments, including MP4s. Open Offline learning; downloaded videos play in the offline workspace. YouTube videos are online only and are never downloaded. Teacher-authored ungraded lesson practice works offline. The four EduMate Kids example activities need the online app and do not sync progress.

Each learner needs a separate managed browser profile. Downloads are stored unencrypted in the browser, may be removed by the browser or user, and can fail if device storage is insufficient. Test the actual tablets, available space, connectivity and synchronization before use. Do not clear browser data while work is pending. Video playback depends on the tablet's MP4 codecs. Downloaded files may remain in an offline profile after a school revokes access; manage devices and clear local data when appropriate.

MP4 uploads are checked for an MP4 container header and size; this is not a malware scan, complete codec check, or proof of copyright permission. Processing currently buffers uploads and downloads in server memory, so evaluate larger-scale usage before a production rollout. Schools must supply approved videos; no sample video files are bundled. YouTube is an external service with its own terms and privacy practices. The app loads the embed only after a user clicks to open it.

Use `python -m alembic upgrade head` in the backend before starting the updated application. On Render, the configured backend start command runs migrations. Set up private S3-compatible storage as described in DEPLOYMENT.md. 
