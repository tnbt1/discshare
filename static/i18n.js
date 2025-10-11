const MESSAGES = {
    en: {
        'upload.title': 'File Transfer',
        'upload.subtitle': 'Simple, Secure, Fast',
        'upload.select_file': 'Select File',
        'upload.drag_drop': 'or drag and drop here',
        'upload.button': 'Upload',
        'upload.uploading': 'Uploading...',
        'upload.scanning': 'Scanning and Uploading...',
        'upload.complete': 'Upload Complete',
        'upload.completed': 'Complete',

        'progress.preparing': 'Preparing scan...',
        'progress.uploading': 'Uploading...',
        'progress.hashing': 'Calculating hash...',
        'progress.blacklist': 'Checking blacklist...',
        'progress.clamav': 'ClamAV scanning...',
        'progress.virustotal': 'VirusTotal checking...',
        'progress.saving': 'Saving file...',
        'progress.finalizing': 'Final check...',

        'error.file_too_large': 'File size exceeds 5GB',
        'error.upload_failed': 'Upload failed',
        'error.communication_error': 'Communication error occurred',

        'scan.safe': '✓ Safe',
        'scan.clean': 'Clean',
        'scan.suspicious': '⚠ Caution',
        'scan.suspicious_desc': 'File may be suspicious',
        'scan.verified': 'Verified',

        'info.file_size': 'File Size',
        'info.status': 'Status',
        'info.ready': 'Ready',
        'info.download_url': 'Download URL',
        'info.clamav': 'ClamAV',
        'info.virustotal': 'VirusTotal',

        'button.copy_url': 'Copy URL',
        'button.copied': 'Copied',
        'button.new_file': 'New File',

        'security.virus_scan': 'Virus Scan Enabled',
        'security.max_size': 'Maximum File Size: 5GB',
        'security.expiry': 'Expiry: ',
        'security.supported_formats': 'Supported Formats: PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML',
    },
    ja: {
        'upload.title': 'ファイル転送',
        'upload.subtitle': 'シンプル、安全、高速',
        'upload.select_file': 'ファイルを選択',
        'upload.drag_drop': 'またはここにドラッグ＆ドロップ',
        'upload.button': 'アップロード',
        'upload.uploading': 'アップロード中...',
        'upload.scanning': 'スキャン・アップロード中...',
        'upload.complete': 'アップロード完了',
        'upload.completed': '完了',

        'progress.preparing': 'スキャン準備中...',
        'progress.uploading': 'アップロード中...',
        'progress.hashing': 'ハッシュ計算中...',
        'progress.blacklist': 'ブラックリストチェック中...',
        'progress.clamav': 'ClamAVスキャン中...',
        'progress.virustotal': 'VirusTotalチェック中...',
        'progress.saving': 'ファイル保存中...',
        'progress.finalizing': '最終判定中...',

        'error.file_too_large': 'ファイルサイズが5GBを超えています',
        'error.upload_failed': 'アップロードに失敗しました',
        'error.communication_error': '通信エラーが発生しました',

        'scan.safe': '✓ 安全',
        'scan.clean': 'クリーン',
        'scan.suspicious': '⚠ 注意',
        'scan.suspicious_desc': '疑わしいファイルの可能性があります',
        'scan.verified': '確認済み',

        'info.file_size': 'ファイルサイズ',
        'info.status': 'ステータス',
        'info.ready': '準備完了',
        'info.download_url': 'ダウンロードURL',
        'info.clamav': 'ClamAV',
        'info.virustotal': 'VirusTotal',

        'button.copy_url': 'URLをコピー',
        'button.copied': 'コピーしました',
        'button.new_file': '新しいファイル',

        'security.virus_scan': 'ウイルススキャン対応',
        'security.max_size': '最大ファイルサイズ: 5GB',
        'security.expiry': '有効期限: ',
        'security.supported_formats': '対応形式: PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML',
    }
};

class I18n {
    constructor() {
        this.currentLang = this.detectLanguage();
    }

    detectLanguage() {
        const browserLang = navigator.language || navigator.userLanguage;
        if (browserLang.startsWith('ja')) {
            return 'ja';
        }
        return 'en';
    }

    setLanguage(lang) {
        if (lang in MESSAGES) {
            this.currentLang = lang;
            localStorage.setItem('app_language', lang);
        }
    }

    getLanguage() {
        return this.currentLang;
    }

    t(key, params = {}) {
        const messages = MESSAGES[this.currentLang] || MESSAGES.en;
        let message = messages[key] || key;

        Object.keys(params).forEach(param => {
            message = message.replace(`{${param}}`, params[param]);
        });

        return message;
    }

    isSupported(lang) {
        return lang in MESSAGES;
    }
}

const i18n = new I18n();

const savedLang = localStorage.getItem('app_language');
if (savedLang && i18n.isSupported(savedLang)) {
    i18n.setLanguage(savedLang);
}

window.i18n = i18n;
