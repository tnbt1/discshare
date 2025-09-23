# DiscShare

Discord Bot経由で大きな容量のファイルを安全に共有するサービスです

## 機能

- 最大5GBまでのファイル転送
- ClamAV + VirusTotal でウイルススキャン
- 3日間の自動削除
- Discord Botコマンドで簡単操作

## 使い方

### Discord Botコマンド

```
/upload - アップロードURL生成
/help - ヘルプ表示
```

### セットアップ

1. `.env`ファイルを作成
```bash
cp .env.example .env
```

2. docker
```bash
docker compose up -d
```
## 必要な環境

minio 又は aws s3にアクセスできる環境が必要です

## 必要な環境変数

### Discord Bot設定
| 変数名 | 説明 | 必須 |
|--------|------|------|
| `DISCORD_TOKEN` | Discord BotのToken | ✅ |
| `REQUIRED_ROLE` | URL生成に必要なロール名 | ✅ |

### ストレージ設定
| 変数名 | 説明 | 必須 |
|--------|------|------|
| `REDIS_URL` | Redisサーバー接続URL | ✅ |
| `MINIO_ENDPOINT` | MinIOサーバーアドレス | ✅ |
| `MINIO_ACCESS_KEY` | MinIOアクセスキー | ✅ |
| `MINIO_SECRET_KEY` | MinIOシークレットキー | ✅ |

### サービス設定
| 変数名 | 説明 | デフォルト |
|--------|------|------------|
| `SERVICE_URL` | 公開URL（Discord表示用） | 必須 |
| `API_PORT` | APIポート番号 | 8000 |
| `MAX_FILE_SIZE` | 最大ファイルサイズ（バイト） | 5GB |
| `URL_EXPIRY_DAYS` | URL有効期限（日数） | 3 |
| `LOG_LEVEL` | ログレベル（DEBUG/INFO/WARNING/ERROR） | INFO |

### セキュリティ設定
| 変数名 | 説明 | デフォルト |
|--------|------|------------|
| `VIRUSTOTAL_API_KEY` | VirusTotal APIキー（空=無効） | 空 |
| `CLAMAV_HOST` | ClamAVホスト名 | clamav |
| `CLAMAV_PORT` | ClamAVポート番号 | 3310 |
| `CLAMAV_TIMEOUT` | スキャンタイムアウト（秒） | 300 |
| `ALLOW_PENDING_DOWNLOAD` | スキャン中のダウンロード許可 | false |
| `SECRET_KEY` | セッション暗号化キー | ランダム生成推奨 |
| `CORS_ORIGINS` | CORS許可オリジン | SERVICE_URLと同じ |

### その他の設定
| 変数名 | 説明 | デフォルト |
|--------|------|------------|
| `SCAN_LOG_DB_PATH` | スキャンログDB保存パス | db/scan_logs.db |
| `SCAN_LOG_RETENTION_DAYS` | ログ保持日数 | 365 |
| `RATE_LIMIT_ENABLED` | レート制限有効化 | true |
| `RATE_LIMIT_PER_HOUR` | 時間あたりの最大リクエスト数 | 10 |
| `DEBUG` | デバッグモード | false |
