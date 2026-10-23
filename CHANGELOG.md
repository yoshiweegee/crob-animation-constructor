## Version 1.1
 - Changed animation format option's short form from `-af` to `-f` to better match short argument stacking behavior
 - Add helpful error message when the pillow package isn't installed
 - By default, restrict framerate for GIF animations to be at maximum 50 FPS to prevent erroneous display in most programs
   - Added command line option `--accurate-frame-delay`/`-A` to explicitly indicate if this behavior is desired or not 
 - Remove unnecessary storage of frames, as ImageMagick requires files anyway. This should reduce overall memory usage

## Version 1.0.1
 - Fix the first frame from having twice the delay it should have

## Version 1.0.0
 - Initial public release