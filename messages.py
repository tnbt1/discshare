from typing import Dict
from config import Config

MESSAGES: Dict[str, Dict[str, str]] = {
    "discord.upload.title": {
        "en": "📁 Upload URL Generated",
        "ja": "📁 アップロードURL生成完了"
    },
    "discord.upload.click_here": {
        "en": "**Click here to upload**",
        "ja": "**ここをクリックしてアップロード**"
    },
    "discord.upload.url_label": {
        "en": "🔗 URL (for copying)",
        "ja": "🔗 URL（コピー用）"
    },
    "discord.upload.expiry": {
        "en": "⏰ Expiry",
        "ja": "⏰ 有効期限"
    },
    "discord.upload.expiry_days": {
        "en": "{days} days",
        "ja": "{days}日間"
    },
    "discord.upload.max_size": {
        "en": "📦 Maximum Size",
        "ja": "📦 最大サイズ"
    },
    "discord.upload.supported_files": {
        "en": "Supported Files",
        "ja": "対応ファイル"
    },
    "discord.upload.supported_formats": {
        "en": "PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML",
        "ja": "PDF, DOCX, XLSX, ZIP, JPG, PNG, MP4, AVI, MOV, MKV, WEBM, TXT, CSV, JSON, XML"
    },
    "discord.upload.footer": {
        "en": "URL can be used multiple times until expiry",
        "ja": "URLは有効期限まで何度でも使用可能です"
    },
    "discord.error.no_permission": {
        "en": "❌ You do not have permission to use this command",
        "ja": "❌ このコマンドを実行する権限がありません"
    },
    "discord.error.generation_failed": {
        "en": "❌ Failed to generate URL",
        "ja": "❌ URL生成に失敗しました"
    },
    "discord.error.service_unavailable": {
        "en": "❌ Cannot connect to service",
        "ja": "❌ サービスに接続できません"
    },
    "discord.help.title": {
        "en": "📖 File Sharing Service Guide",
        "ja": "📖 ファイル共有サービスの使い方"
    },
    "discord.help.upload_command": {
        "en": "/upload",
        "ja": "/upload"
    },
    "discord.help.upload_desc": {
        "en": "Generate upload URL",
        "ja": "アップロード用URLを生成します"
    },
    "discord.help.required_role": {
        "en": "Required Role",
        "ja": "必要な権限"
    },
    "frontend.upload.title": {
        "en": "File Transfer",
        "ja": "ファイル転送"
    },
    "frontend.upload.subtitle": {
        "en": "Simple, Secure, Fast",
        "ja": "シンプル、安全、高速"
    },
    "frontend.upload.select_file": {
        "en": "Select File",
        "ja": "ファイルを選択"
    },
    "frontend.upload.drag_drop": {
        "en": "or drag and drop here",
        "ja": "またはここにドラッグ＆ドロップ"
    },
    "frontend.upload.uploading": {
        "en": "Uploading...",
        "ja": "アップロード中..."
    },
    "frontend.upload.scanning": {
        "en": "Scanning and Uploading...",
        "ja": "スキャン・アップロード中..."
    },
    "frontend.upload.complete": {
        "en": "Upload Complete",
        "ja": "アップロード完了"
    },
    "frontend.upload.completed": {
        "en": "Complete",
        "ja": "完了"
    },
    "frontend.error.file_too_large": {
        "en": "File size exceeds 5GB",
        "ja": "ファイルサイズが5GBを超えています"
    },
    "frontend.error.upload_failed": {
        "en": "Upload failed",
        "ja": "アップロードに失敗しました"
    },
    "frontend.error.communication_error": {
        "en": "Communication error occurred",
        "ja": "通信エラーが発生しました"
    },
    "frontend.scan.safe": {
        "en": "✓ Safe",
        "ja": "✓ 安全"
    },
    "frontend.scan.suspicious": {
        "en": "⚠ Caution",
        "ja": "⚠ 注意"
    },
    "frontend.scan.suspicious_desc": {
        "en": "File may be suspicious",
        "ja": "疑わしいファイルの可能性があります"
    },
    "frontend.info.file_size": {
        "en": "File Size",
        "ja": "ファイルサイズ"
    },
    "frontend.info.status": {
        "en": "Status",
        "ja": "ステータス"
    },
    "frontend.info.ready": {
        "en": "Ready",
        "ja": "準備完了"
    },
    "frontend.info.download_url": {
        "en": "Download URL",
        "ja": "ダウンロードURL"
    },
    "frontend.button.copy_url": {
        "en": "Copy URL",
        "ja": "URLをコピー"
    },
    "frontend.button.copied": {
        "en": "Copied",
        "ja": "コピーしました"
    },
    "frontend.button.new_file": {
        "en": "New File",
        "ja": "新しいファイル"
    },
    "frontend.progress.preparing": {
        "en": "Preparing scan...",
        "ja": "スキャン準備中..."
    },
    "frontend.progress.hashing": {
        "en": "Calculating hash...",
        "ja": "ハッシュ計算中..."
    },
    "frontend.progress.blacklist_check": {
        "en": "Checking blacklist...",
        "ja": "ブラックリストチェック中..."
    },
    "frontend.progress.clamav_scanning": {
        "en": "ClamAV scanning...",
        "ja": "ClamAVスキャン中..."
    },
    "frontend.progress.virustotal_check": {
        "en": "VirusTotal checking...",
        "ja": "VirusTotalチェック中..."
    },
    "frontend.progress.saving_file": {
        "en": "Saving file...",
        "ja": "ファイル保存中..."
    },
    "frontend.progress.final_check": {
        "en": "Final check...",
        "ja": "最終判定中..."
    },
}


def get_message(key: str, lang: str = None, **kwargs) -> str:
    if lang is None:
        lang = Config.APP_LANGUAGE

    if key in MESSAGES:
        message = MESSAGES[key].get(lang) or MESSAGES[key].get('en') or key
    else:
        message = key

    if kwargs:
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass

    return message


def get_user_language() -> str:
    return Config.APP_LANGUAGE
