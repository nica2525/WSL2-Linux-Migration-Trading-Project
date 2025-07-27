// JamesORB監視ダッシュボード Service Worker - kiro設計準拠
const CACHE_NAME = 'jamesorb-dashboard-v1.0';
const CACHE_VERSION = '1.0.0';

// キャッシュするリソース - オフライン対応
const urlsToCache = [
    '/',
    '/mobile',
    '/static/css/dashboard.css',
    '/static/js/dashboard.js',
    '/static/js/service-worker.js',
    '/static/icons/icon-192x192.png',
    '/manifest.json',
    // CDN リソース（オフライン時フォールバック用）
    'https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// インストール時のキャッシュ
self.addEventListener('install', event => {
    console.log('📱 Service Worker: インストール開始');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('📱 Service Worker: キャッシュ作成');
                return cache.addAll(urlsToCache.filter(url => !url.startsWith('https://')));
            })
            .then(() => {
                console.log('📱 Service Worker: インストール完了');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('📱 Service Worker: インストールエラー', error);
            })
    );
});

// アクティベーション時の古いキャッシュ削除
self.addEventListener('activate', event => {
    console.log('📱 Service Worker: アクティベーション開始');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME) {
                            console.log('📱 Service Worker: 古いキャッシュ削除', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('📱 Service Worker: アクティベーション完了');
                return self.clients.claim();
            })
    );
});

// フェッチ時のキャッシュ戦略 - kiro設計のオフライン対応
self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);
    
    // API リクエストの処理
    if (requestUrl.pathname.startsWith('/api/')) {
        event.respondWith(
            // ネットワーク優先、フォールバックでキャッシュ
            networkFirstStrategy(event.request)
        );
        return;
    }
    
    // WebSocket は無視
    if (requestUrl.pathname.includes('socket.io')) {
        return;
    }
    
    // 静的リソースの処理
    event.respondWith(
        // キャッシュ優先、フォールバックでネットワーク
        cacheFirstStrategy(event.request)
    );
});

// ネットワーク優先戦略（API用）
async function networkFirstStrategy(request) {
    try {
        const response = await fetch(request);
        
        // 成功時はキャッシュに保存
        if (response && response.status === 200) {
            const responseClone = response.clone();
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, responseClone);
        }
        
        return response;
    } catch (error) {
        console.log('📱 Service Worker: ネットワークエラー、キャッシュから取得', request.url);
        
        // ネットワークエラー時はキャッシュから取得
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // キャッシュもない場合はオフライン応答
        return createOfflineResponse(request);
    }
}

// キャッシュ優先戦略（静的リソース用）
async function cacheFirstStrategy(request) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
        // バックグラウンドでキャッシュ更新
        updateCacheInBackground(request);
        return cachedResponse;
    }
    
    // キャッシュにない場合はネットワークから取得
    try {
        const response = await fetch(request);
        
        if (response && response.status === 200) {
            const responseClone = response.clone();
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, responseClone);
        }
        
        return response;
    } catch (error) {
        console.log('📱 Service Worker: リソース取得エラー', request.url);
        return createOfflineResponse(request);
    }
}

// バックグラウンドキャッシュ更新
async function updateCacheInBackground(request) {
    try {
        const response = await fetch(request);
        if (response && response.status === 200) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response);
        }
    } catch (error) {
        // バックグラウンド更新のエラーは無視
    }
}

// オフライン時の応答作成
function createOfflineResponse(request) {
    const requestUrl = new URL(request.url);
    
    // API リクエストの場合
    if (requestUrl.pathname.startsWith('/api/')) {
        return new Response(
            JSON.stringify({
                error: 'オフラインです',
                offline: true,
                timestamp: new Date().toISOString()
            }),
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            }
        );
    }
    
    // HTML ページの場合
    if (request.headers.get('accept')?.includes('text/html')) {
        return new Response(
            `
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>オフライン - JamesORB</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-align: center;
                        padding: 50px 20px;
                        margin: 0;
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .offline-icon {
                        font-size: 64px;
                        margin-bottom: 24px;
                    }
                    .offline-title {
                        font-size: 24px;
                        font-weight: 600;
                        margin-bottom: 16px;
                    }
                    .offline-message {
                        font-size: 16px;
                        opacity: 0.8;
                        margin-bottom: 32px;
                    }
                    .retry-btn {
                        background: rgba(255, 255, 255, 0.2);
                        color: white;
                        border: 2px solid rgba(255, 255, 255, 0.3);
                        padding: 12px 24px;
                        border-radius: 25px;
                        font-size: 16px;
                        cursor: pointer;
                        transition: all 0.3s ease;
                    }
                    .retry-btn:hover {
                        background: rgba(255, 255, 255, 0.3);
                    }
                </style>
            </head>
            <body>
                <div class="offline-icon">📡</div>
                <div class="offline-title">オフラインです</div>
                <div class="offline-message">
                    インターネット接続を確認して<br>
                    再度お試しください
                </div>
                <button class="retry-btn" onclick="window.location.reload()">
                    再試行
                </button>
                
                <script>
                    // オンライン復帰時の自動リロード
                    window.addEventListener('online', () => {
                        window.location.reload();
                    });
                </script>
            </body>
            </html>
            `,
            {
                status: 503,
                statusText: 'Service Unavailable',
                headers: {
                    'Content-Type': 'text/html',
                    'Cache-Control': 'no-cache'
                }
            }
        );
    }
    
    // その他のリソース
    return new Response('オフライン', {
        status: 503,
        statusText: 'Service Unavailable'
    });
}

// プッシュ通知（将来の拡張用）
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        
        const options = {
            body: data.message || 'JamesORBからの通知',
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-192x192.png',
            vibrate: [200, 100, 200],
            tag: 'jamesorb-notification',
            actions: [
                {
                    action: 'open',
                    title: 'ダッシュボードを開く'
                },
                {
                    action: 'close',
                    title: '閉じる'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification('JamesORB監視', options)
        );
    }
});

// 通知クリック処理
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'open') {
        event.waitUntil(
            clients.openWindow('/mobile')
        );
    }
});

// メッセージ処理（クライアントとの通信用）
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({
            version: CACHE_VERSION,
            cacheName: CACHE_NAME
        });
    }
});

console.log('📱 Service Worker: ロード完了 - JamesORB監視ダッシュボード v' + CACHE_VERSION);