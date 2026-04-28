import os
import ffmpeg

def mp3_to_video(mp3_path: str, output_name: str) -> str:
    """
    Convert MP3 narration into MP4 video using FFmpeg.

    Creates a simple video with a black background and audio from the MP3.
    Output format: MP4. Saves under the 'output/' directory.

    Args:
        mp3_path (str): Path to the input MP3 file.
        output_name (str): Desired name for the output MP4 file (e.g., "video.mp4").

    Returns:
        str: Path to the created MP4 file.
    """
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_mp4_path = os.path.join(output_dir, output_name)

    # Get audio duration to set video duration
    probe = ffmpeg.probe(mp3_path)
    duration = float(probe['streams'][0]['duration'])

    # Create a black background video stream
    # -f lavfi: input from libavfilter
    # -i color=c=black:s=1920x1080:d={duration}: generate a black color stream with resolution 1920x1080 for the calculated duration
    video_input = ffmpeg.input(f'color=c=black:s=1920x1080:d={duration}', f='lavfi')
    
    # Input audio stream
    audio_input = ffmpeg.input(mp3_path)

    # Merge video and audio streams
    # -c:v libx264: encode video with h.264
    # -c:a aac: encode audio with aac
    # -pix_fmt yuv420p: pixel format, often required for wider compatibility
    (
        ffmpeg
        .output(video_input, audio_input, output_mp4_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', shortest=None)
        .run(overwrite_output=True)
    )

    return output_mp4_path
