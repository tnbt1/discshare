document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const message = document.getElementById('message');
    const selectedFileDiv = document.getElementById('selectedFile');
    
    let selectedFile = null;
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragging');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragging');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragging');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        selectedFile = file;
        selectedFileDiv.innerHTML = `
            <div class="selected-file">
                <div class="file-details">
                    <div class="file-icon">📄</div>
                    <div>
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${formatFileSize(file.size)}</div>
                    </div>
                </div>
                <div class="remove-file" onclick="removeFile()">✕</div>
            </div>
        `;
        
        uploadBtn.disabled = false;
        message.innerHTML = '';
    }

    window.removeFile = function() {
        selectedFile = null;
        selectedFileDiv.innerHTML = '';
        uploadBtn.disabled = true;
        fileInput.value = '';
    }
    function formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
        return (bytes / 1073741824).toFixed(2) + ' GB';
    }

    uploadBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        if (selectedFile.size > 5 * 1024 * 1024 * 1024) {
            showError('ファイルサイズが5GBを超えています');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'アップロード中...';
        progressContainer.style.display = 'block';
        message.innerHTML = '';

        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = Math.round(percentComplete) + '%';
            }
        });
        
        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                showSuccess(result);
            } else {
                try {
                    const error = JSON.parse(xhr.responseText);
                    showError(error.detail || 'アップロードに失敗しました');
                } catch {
                    showError('アップロードに失敗しました');
                }
            }
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'アップロード';
        });
        
        xhr.addEventListener('error', function() {
            showError('通信エラーが発生しました');
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'アップロード';
        });
        
        xhr.open('POST', `/api/upload/${token}`);
        xhr.send(formData);
    });

    function showSuccess(result) {
        progressFill.style.width = '100%';
        progressText.textContent = '完了';
        uploadArea.style.display = 'none';
        selectedFileDiv.style.display = 'none';
        uploadBtn.style.display = 'none';
        
        message.innerHTML = `
            <div style="text-align: center; padding: 40px 0;">
                <div style="width: 80px; height: 80px; margin: 0 auto 24px; background: linear-gradient(135deg, #34C759, #30D158); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-size: 40px;">✓</span>
                </div>
                <h2 style="font-size: 28px; font-weight: 600; margin-bottom: 12px;">アップロード完了</h2>
                <p style="color: #86868b; margin-bottom: 32px; font-size: 17px;">${result.filename}</p>
                
                <div style="background: #f5f5f7; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="color: #86868b; font-size: 15px;">ファイルサイズ</span>
                        <span style="font-weight: 500; font-size: 15px;">${formatFileSize(result.size)}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #86868b; font-size: 15px;">ステータス</span>
                        <span style="color: #34C759; font-weight: 500; font-size: 15px;">準備完了</span>
                    </div>
                </div>
                
                <div style="margin-bottom: 24px;">
                    <p style="color: #86868b; font-size: 14px; margin-bottom: 8px;">ダウンロードURL</p>
                    <div class="url-display">${window.location.origin}${result.download_url}</div>
                </div>
                
                <button class="btn" onclick="copyUrl('${window.location.origin}${result.download_url}')" style="margin-right: 8px;">
                    URLをコピー
                </button>
                <button class="btn" onclick="location.reload()" style="background: #f5f5f7; color: #000;">
                    新しいファイル
                </button>
            </div>
        `;
        
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000);
    }

    function showError(errorMessage) {
        message.innerHTML = `
            <div class="message error">
                <div style="display: flex; align-items: center;">
                    <span style="margin-right: 8px; font-size: 18px;">⚠️</span>
                    <span>${errorMessage}</span>
                </div>
            </div>
        `;
        progressContainer.style.display = 'none';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
    }
});

function copyUrl(url) {
    const textarea = document.createElement('textarea');
    textarea.value = url;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);

    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = 'コピーしました';
    btn.style.background = '#34C759';
    
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
    }, 2000);
}
