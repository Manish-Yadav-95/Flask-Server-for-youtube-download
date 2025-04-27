from flask import Flask, render_template_string, request, jsonify, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)

# HTML Template
html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>YouTube Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen flex flex-col items-center py-10 px-4">

    <h1 class="text-3xl font-bold mb-6 text-center">YouTube Video Downloader</h1>

    <div class="w-full max-w-md">
        <input id="urlInput" type="text" placeholder="Paste YouTube URL here..."
               class="w-full p-3 rounded-xl border shadow focus:outline-none focus:ring-2 focus:ring-blue-400 mb-4">
        <button onclick="getFormats()"
                class="w-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-indigo-600 hover:to-blue-500 text-white py-3 rounded-xl font-bold text-lg transition-all duration-300">
            Fetch Download Options
        </button>
    </div>

    <div id="loadingSpinner" class="hidden mt-10 flex justify-center items-center">
        <div class="loader ease-linear rounded-full border-8 border-t-8 border-gray-200 h-24 w-24"></div>
        <p class="ml-4 text-lg font-semibold">Fetching Download Options...</p>
    </div>

    <div id="thumbnailContainer" class="mt-10"></div>

    <div id="formatsDiv" class="mt-6 grid gap-6 w-full max-w-2xl"></div>

    <!-- Toast Notification -->
    <div id="toast" class="hidden fixed top-6 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 opacity-0 transition-all duration-500"></div>

    <style>
        .loader {
            border-top-color: #3490dc;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .animate-fadeIn {
            animation: fadeIn 0.5s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
    </style>

    <script>
        function showLoading(text) {
            document.getElementById('loadingSpinner').classList.remove('hidden');
            document.querySelector('#loadingSpinner p').textContent = text;
        }

        function hideLoading() {
            document.getElementById('loadingSpinner').classList.add('hidden');
        }

        function showToast(message, color = 'red') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = `fixed top-6 left-1/2 transform -translate-x-1/2 bg-${color}-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 opacity-0 transition-all duration-500`;

            toast.classList.remove('hidden');
            setTimeout(() => {
                toast.classList.add('opacity-100');
            }, 50);

            setTimeout(() => {
                toast.classList.remove('opacity-100');
                setTimeout(() => {
                    toast.classList.add('hidden');
                }, 500);
            }, 3000);
        }

        async function getFormats() {
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                showToast("Please paste a YouTube link!");
                return;
            }

            const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
            if (!youtubeRegex.test(url)) {
                showToast("Please enter a valid YouTube URL!");
                return;
            }

            showLoading("Analyzing YouTube Link");

            try {
                const response = await fetch('/formats', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await response.json();
                hideLoading();

                if (!data.success) {
                    showToast("Invalid YouTube link or unable to fetch video. Please try again!");
                    return;
                }

                const thumbnailHTML = `
                    <img src="${data.thumbnail}" alt="Thumbnail" 
                        class="rounded-xl shadow-md hover:shadow-lg transition-shadow duration-300 max-w-xs md:max-w-sm mx-auto mb-4 animate-fadeIn">
                    <h2 class="text-2xl font-bold text-gray-800 mb-4 text-center">${data.title}</h2>
                `;
                document.getElementById('thumbnailContainer').innerHTML = thumbnailHTML;

                let formatsHTML = "";
                for (const format of data.formats) {
                    formatsHTML += `
                        <div class="bg-white p-4 rounded-xl shadow-md mb-4 hover:shadow-lg transition transform hover:scale-105 animate-fadeIn">
                            <p><strong>Format:</strong> ${format.ext.toUpperCase()}</p>
                            <p><strong>Resolution:</strong> ${format.resolution}</p>
                            <p><strong>Size:</strong> ${format.filesize} MB</p>
                            <button onclick="downloadVideo('${url}', '${format.format_id}')" 
                                class="bg-gradient-to-r from-green-400 to-blue-500 hover:from-green-500 hover:to-blue-600 text-white font-bold py-2 px-6 rounded-full shadow-md w-full mt-4 transform hover:scale-105 transition-all duration-300 ease-in-out">
                                Download
                            </button>
                        </div>
                    `;
                }
                document.getElementById('formatsDiv').innerHTML = formatsHTML;

            } catch (error) {
                hideLoading();
                showToast("Something went wrong. Please check your link and try again!");
            }
        }

        function downloadVideo(url, format_id) {
            window.location.href = `/download?url=${encodeURIComponent(url)}&format_id=${format_id}`;
        }
    </script>

</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(html_template)

@app.route('/formats', methods=['POST'])
def formats():
    data = request.get_json()
    url = data.get('url')

    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []
        for f in info['formats']:
            if f.get('filesize') and f.get('format_id') and f.get('ext'):
                formats.append({
                    'format_id': f['format_id'],
                    'ext': f['ext'],
                    'resolution': f.get('resolution', f"{f.get('width', 'unknown')}x{f.get('height', 'unknown')}"),
                    'filesize': round(f['filesize'] / 1024 / 1024, 2)  # MB
                })

        return jsonify({
            'success': True,
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'formats': formats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/download')
def download():
    url = request.args.get('url')
    format_id = request.args.get('format_id')
    temp_filename = f"{uuid.uuid4()}.%(ext)s"
    
    ydl_opts = {
        'format': format_id,
        'outtmpl': temp_filename,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        downloaded_filename = temp_filename.replace('%(ext)s', info['ext'])

        return send_file(downloaded_filename, as_attachment=True)
    finally:
        try:
            os.remove(downloaded_filename)
        except Exception:
            pass

if __name__ == '__main__':
    app.run(debug=True)