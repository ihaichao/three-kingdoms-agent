/**
 * 后端地址的唯一来源。
 *
 * 原来的写法是在两个文件里各自拼一遍：
 *     `http://${hostname.replace('8080', '8000')}`
 * 那是给 GitHub Codespaces 那种「同主机不同端口」的环境写的。上了反向代理
 * 之后端口从 URL 里消失，replace 匹配不到任何东西，地址直接错。
 *
 * 而且 https 分支里返回的还是 `ws://`——页面一旦是 https，浏览器会以
 * 混合内容为由直接拒掉这个连接。**现在这份代码部署到任何 HTTPS 环境都连不上
 * WebSocket**，本地开发看不出来，因为本地是 http。
 *
 * 现在改成构建期注入：
 *     API_BASE_URL=https://api.example.com npm run build
 * 不传就回落到 http://localhost:8000，本地开发行为不变。
 */

// webpack DefinePlugin 会在构建时把 __API_BASE_URL__ 替换成字符串字面量。
// eslint-disable-next-line no-undef
const CONFIGURED = typeof __API_BASE_URL__ !== 'undefined' ? __API_BASE_URL__ : '';

export const API_BASE_URL = CONFIGURED || 'http://localhost:8000';

/**
 * 从 HTTP 地址推导 WebSocket 地址。
 *
 * http -> ws, https -> wss。用 startsWith 而不是 replace('http','ws')：
 * 后者会把 'https://x.com/http-demo' 里的第二个 http 也换掉。
 */
export const WS_BASE_URL = API_BASE_URL.startsWith('https://')
  ? `wss://${API_BASE_URL.slice('https://'.length)}`
  : `ws://${API_BASE_URL.slice('http://'.length)}`;
