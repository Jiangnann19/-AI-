// 全局状态
let conversationHistory = [];
let uploadedFiles = [];
let currentIntent = {};
let generatedFiles = {
    ppt: null,
    word: null,
    game: null
};

// 切换标签页
function switchTab(tabName) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // 移除所有导航按钮的激活状态
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 显示选中的标签内容
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // 激活对应的导航按钮
    event.target.classList.add('active');
}

// 切换预览标签
function switchPreview(previewType) {
    // 隐藏所有预览内容
    document.querySelectorAll('.preview-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // 移除所有预览按钮的激活状态
    document.querySelectorAll('.preview-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // 显示选中的预览内容
    document.getElementById(previewType + '-preview').classList.add('active');
    
    // 激活对应的预览按钮
    event.target.classList.add('active');
}

// 处理回车键
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// 发送消息
function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // 添加用户消息到界面
    addMessageToChat('user', message);
    
    // 清空输入框
    input.value = '';
    
    // 发送到后端
    processMessage(message);
}

// 添加消息到聊天界面
function addMessageToChat(role, content) {
    const chatHistory = document.getElementById('chat-history');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = content.replace(/\n/g, '<br>');
    
    messageDiv.appendChild(contentDiv);
    chatHistory.appendChild(messageDiv);
    
    // 滚动到底部
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    // 添加到历史记录
    conversationHistory.push({
        role: role,
        content: content
    });
}

// 处理消息（调用后端API）
async function processMessage(message) {
    showLoading();
    
    // 获取RAG开关状态
    const ragEnabled = document.getElementById('rag-enabled').checked;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: conversationHistory,
                files: uploadedFiles,
                rag_enabled: ragEnabled
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            let responseText = data.response;
            
            // 如果使用了RAG，添加来源标注
            if (data.used_rag) {
                responseText += '\n\n【参考资料：本地知识库上传文档】';
            } else if (data.rag_error) {
                responseText += '\n\n【知识库未检索到匹配资料，将使用模型原生知识回答】';
            }
            
            addMessageToChat('assistant', responseText);
            
            // 更新当前意图
            if (data.intent) {
                currentIntent = data.intent;
                
                // 根据后端返回的is_complete状态检查是否可以生成课件
                checkCanGenerate(data.is_complete);
            }
        } else {
            addMessageToChat('assistant', '抱歉，处理您的请求时出错：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('assistant', '抱歉，网络连接出现问题，请稍后重试。');
    }
    
    hideLoading();
}

// 检查是否可以生成课件
function checkCanGenerate(isComplete) {
    const generateBtn = document.getElementById('generate-btn');
    
    // 根据后端返回的is_complete状态决定按钮是否可用
    if (isComplete === true) {
        generateBtn.disabled = false;
    } else {
        generateBtn.disabled = true;
    }
}

// 语音输入
function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('您的浏览器不支持语音识别功能，请使用Chrome浏览器。');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.lang = 'zh-CN';
    recognition.continuous = false;
    recognition.interimResults = false;
    
    recognition.onstart = function() {
        addMessageToChat('assistant', '🎤 正在聆听，请说话...');
    };
    
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('user-input').value = transcript;
    };
    
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        addMessageToChat('assistant', '语音识别失败，请重试或使用文字输入。');
    };
    
    recognition.onend = function() {
        // 识别结束
    };
    
    recognition.start();
}

// 处理文件上传
function handleFileUpload(event) {
    const files = event.target.files;
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // 检查是否是图片文件
        if (file.type.startsWith('image/')) {
            // 上传图片并进行解析
            uploadAndParseImage(file);
        } else {
            // 普通文件，直接添加到列表
            uploadedFiles.push(file);
            displayUploadedFile(file);
        }
    }
    
    // 更新文件状态
    updateFileStatus();
}

// 上传并解析图片
async function uploadAndParseImage(file) {
    const formData = new FormData();
    formData.append('image', file);
    
    try {
        showLoading();
        
        const response = await fetch('/api/parse-image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 显示图片预览
            displayImagePreview(file, data.parsed_text);
            
            // 将解析结果添加到消息历史
            addMessageToChat('user', `[上传图片: ${file.name}]`);
            addMessageToChat('assistant', `✅ 图片解析成功（DashScope qwen3.7-plus）\n\n${data.parsed_text}\n\n💡 提示：您可以询问关于这张图片的问题，如"分析这张抓包图的seq、ack数值"`);
            
            // 保存解析结果供后续使用
            uploadedFiles.push({
                name: file.name,
                type: 'image',
                parsed_text: data.parsed_text,
                raw_file: file
            });
            
            // 显示保存到知识库按钮
            showSaveToKBButton(file.name, data.parsed_text);
        } else {
            // 提供友好的错误提示
            let errorMsg = data.error;
            if (errorMsg.includes('API密钥')) {
                errorMsg = '❌ API密钥错误：请在.env文件中设置DASHSCOPE_API_KEY';
            } else if (errorMsg.includes('额度')) {
                errorMsg = '❌ API额度不足：请检查阿里云百炼账户余额';
            } else if (errorMsg.includes('图片过大')) {
                errorMsg = '❌ 图片过大：请上传小于10MB的图片';
            }
            addMessageToChat('assistant', errorMsg);
        }
    } catch (error) {
        console.error('Error parsing image:', error);
        addMessageToChat('assistant', '图片解析时出现错误，请稍后重试。');
    } finally {
        hideLoading();
    }
}

// 显示图片预览
function displayImagePreview(file, parsedText) {
    const container = document.getElementById('uploaded-files');
    const imagePreview = document.createElement('div');
    imagePreview.className = 'image-preview';
    
    const reader = new FileReader();
    reader.onload = function(e) {
        imagePreview.innerHTML = `
            <div class="image-item">
                <img src="${e.target.result}" alt="${file.name}" class="thumbnail">
                <div class="image-info">
                    <span class="image-name">📷 ${file.name}</span>
                    <span class="remove" onclick="removeFile('${file.name}', this)">×</span>
                </div>
                <div class="parsed-text-preview">
                    <details>
                        <summary>查看解析结果（DashScope qwen3.7-plus）</summary>
                        <p>${parsedText}</p>
                    </details>
                </div>
            </div>
        `;
    };
    reader.readAsDataURL(file);
    
    container.appendChild(imagePreview);
}

// 显示保存到知识库按钮
function showSaveToKBButton(fileName, parsedText) {
    const container = document.getElementById('uploaded-files');
    const saveButton = document.createElement('div');
    saveButton.className = 'save-to-kb-area';
    saveButton.id = `save-kb-${fileName}`;
    saveButton.innerHTML = `
        <button class="save-kb-btn" onclick="saveImageToKB('${fileName}')">💾 将DashScope解析结果保存到知识库</button>
    `;
    container.appendChild(saveButton);
    
    // 保存解析结果到全局变量
    window.imageParsedTexts = window.imageParsedTexts || {};
    window.imageParsedTexts[fileName] = parsedText;
}

// 保存图片解析结果到知识库
async function saveImageToKB(fileName) {
    const parsedText = window.imageParsedTexts[fileName];
    
    if (!parsedText) {
        alert('未找到图片解析结果');
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch('/api/save-to-knowledge-base', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: parsedText,
                source: `图片解析: ${fileName}`,
                type: 'image_analysis'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessageToChat('assistant', `✅ 图片解析结果已成功保存到知识库！`);
            
            // 移除保存按钮
            const saveButton = document.getElementById(`save-kb-${fileName}`);
            if (saveButton) {
                saveButton.remove();
            }
            
            // 刷新知识库统计
            loadKnowledgeBaseStats();
        } else {
            addMessageToChat('assistant', `保存到知识库失败：${data.error}`);
        }
    } catch (error) {
        console.error('Error saving to KB:', error);
        addMessageToChat('assistant', '保存到知识库时出现错误，请稍后重试。');
    } finally {
        hideLoading();
    }
}

// 显示上传的文件
function displayUploadedFile(file) {
    const container = document.getElementById('uploaded-files');
    const fileTag = document.createElement('div');
    fileTag.className = 'file-tag';
    fileTag.innerHTML = `
        📄 ${file.name}
        <span class="remove" onclick="removeFile('${file.name}', this)">×</span>
    `;
    container.appendChild(fileTag);
}

// 移除文件
function removeFile(fileName, element) {
    uploadedFiles = uploadedFiles.filter(f => f.name !== fileName);
    element.parentElement.remove();
    updateFileStatus();
}

// 更新文件状态
function updateFileStatus() {
    const status = document.getElementById('file-status');
    if (uploadedFiles.length > 0) {
        status.textContent = `已上传 ${uploadedFiles.length} 个文件`;
    } else {
        status.textContent = '';
    }
}

// 生成课件
async function generateCourseware() {
    showLoading();
    
    // 获取RAG开关状态
    const ragEnabled = document.getElementById('rag-enabled').checked;
    
    try {
        // 创建FormData上传文件
        const formData = new FormData();
        formData.append('intent', JSON.stringify(currentIntent));
        formData.append('rag_enabled', ragEnabled);
        
        uploadedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch('/api/generate', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            let successMessage = '✅ 课件生成成功！您可以在"课件预览"标签页查看和下载生成的课件。';
            
            // 如果使用了RAG，添加来源标注
            if (data.used_rag) {
                successMessage += '\n\n【参考资料：本地知识库上传文档】';
            }
            
            addMessageToChat('assistant', successMessage);
            
            // 保存生成的文件路径
            generatedFiles = {
                ppt: data.ppt_path,
                word: data.word_path,
                game: data.game_path
            };
            
            // 更新预览界面
            updatePreview(data);
        } else {
            addMessageToChat('assistant', '❌ 课件生成失败：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('assistant', '❌ 课件生成时出现网络错误，请稍后重试。');
    }
    
    hideLoading();
}

// 渲染TCP握手幻灯片（左右分栏布局）
function renderTcpHandshakeSlide(slide, index) {
    const title = slide.title || 'TCP三次握手';
    const content = slide.content || '';
    
    return `
        <div class="tcp-header">
            <div class="tcp-title">${title}</div>
            <div class="tcp-subtitle">理解连接建立过程、seq与ack规则，以及为什么需要三次握手</div>
        </div>
        <div class="tcp-divider"></div>
        <div class="tcp-layout">
            <div class="tcp-left">
                <div class="tcp-section-title">知识点讲解</div>
                <div class="tcp-flow-box">
                    <div class="tcp-box-title">三次握手流程</div>
                    <div class="tcp-flow-content">
                        1. 客户端发送<span class="tcp-highlight">SYN</span>，请求建立连接<br>
                        2. 服务端回复<span class="tcp-highlight">SYN+ACK</span>，确认并请求<br>
                        3. 客户端回复<span class="tcp-highlight">ACK</span>，确认连接建立
                    </div>
                </div>
                <div class="tcp-formula-box">
                    <div class="tcp-box-title">seq与ack计算规则</div>
                    <div class="tcp-formula-content">
                        <span class="tcp-highlight">seq</span>：发送方序号 | <span class="tcp-highlight">ack</span> = 对方seq + 1
                    </div>
                </div>
                <div class="tcp-state-box">
                    <div class="tcp-box-title">状态转换</div>
                    <div class="tcp-state-content">
                        CLOSED → SYN_SENT → ESTABLISHED<br>
                        LISTEN → SYN_RCVD → ESTABLISHED
                    </div>
                </div>
                <div class="tcp-wireshark-box">
                    <div class="tcp-box-title">Wireshark抓包图占位</div>
                    <div class="tcp-wireshark-placeholder">
                        [此处显示Wireshark抓包截图]
                    </div>
                </div>
                <div class="tcp-misconception-box">
                    <div class="tcp-box-title">认知误区提示</div>
                    <div class="tcp-misconception-content">
                        ⚠️ 三次握手不是"发三个包"，而是双方确认建立可靠连接的过程
                    </div>
                </div>
            </div>
            <div class="tcp-right">
                <div class="tcp-section-title">TCP握手序号大挑战</div>
                <div class="tcp-game-note">完整答题游戏请打开配套HTML文件</div>
                <div class="tcp-quiz-box">
                    <div class="tcp-question">
                        <div class="tcp-q-title">第1题：TCP第一次握手发送什么报文？</div>
                        <div class="tcp-q-options">A. SYN  B. SYN+ACK  C. ACK  D. FIN</div>
                        <div class="tcp-q-answer">答案：<span class="tcp-answer-correct">A</span></div>
                    </div>
                    <div class="tcp-question">
                        <div class="tcp-q-title">第2题：客户端seq=100，服务端ack是多少？</div>
                        <div class="tcp-q-options">A. 100  B. 101  C. 99  D. 102</div>
                        <div class="tcp-q-answer">答案：<span class="tcp-answer-correct">B</span></div>
                    </div>
                    <div class="tcp-question">
                        <div class="tcp-q-title">第3题：TCP三次握手最主要目的是？</div>
                        <div class="tcp-q-options">A. 加快传输速度  B. 防止失效历史报文  C. 加密传输  D. 校验完整性</div>
                        <div class="tcp-q-answer">答案：<span class="tcp-answer-correct">B</span></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="tcp-footer">
            三次握手的本质：通过双方确认，建立可靠连接，同时协调初始序号。
        </div>
    `;
}

// 更新预览界面
function updatePreview(data) {
    // PPT预览
    if (data.ppt_path) {
        document.getElementById('ppt-placeholder').style.display = 'none';
        document.getElementById('ppt-content').style.display = 'block';
        document.getElementById('ppt-export').style.display = 'block';
        
        // 显示PPT幻灯片预览
        const slidesContainer = document.getElementById('ppt-slides');
        slidesContainer.innerHTML = '';
        
        if (data.ppt_structure && data.ppt_structure.length > 0) {
            data.ppt_structure.forEach((slide, index) => {
                const slideDiv = document.createElement('div');
                const templateType = slide.template_type || slide.slide_type || 'knowledge';
                
                console.log(`网页预览加载的template_type: ${templateType}, 幻灯片标题: ${slide.title}`);
                
                // TCP握手模板使用特殊布局
                if (templateType === 'tcp_handshake') {
                    slideDiv.className = 'ppt-slide tcp-handshake-slide';
                    slideDiv.innerHTML = renderTcpHandshakeSlide(slide, index);
                } else {
                    slideDiv.className = 'ppt-slide';
                    slideDiv.innerHTML = `
                        <div class="slide-number">第 ${index + 1} 页</div>
                        <div class="slide-title">${slide.title || '无标题'}</div>
                        <div class="slide-content">${slide.content || ''}</div>
                    `;
                }
                slidesContainer.appendChild(slideDiv);
            });
        }
    }
    
    // Word预览
    if (data.word_path) {
        document.getElementById('word-placeholder').style.display = 'none';
        document.getElementById('word-content').style.display = 'block';
        document.getElementById('word-export').style.display = 'block';
        
        document.getElementById('word-text').textContent = data.word_preview || '教案内容已生成';
    }
    
    // 游戏预览
    if (data.game_path) {
        document.getElementById('game-placeholder').style.display = 'none';
        document.getElementById('game-content').style.display = 'block';
        document.getElementById('game-export').style.display = 'block';
        
        document.getElementById('game-iframe').src = data.game_path;
    }
}

// 下载PPT
function downloadPPT() {
    if (generatedFiles.ppt) {
        window.open('/api/download/ppt', '_blank');
    }
}

// 下载Word
function downloadWord() {
    if (generatedFiles.word) {
        window.open('/api/download/word', '_blank');
    }
}

// 下载游戏
function downloadGame() {
    if (generatedFiles.game) {
        window.open('/api/download/game', '_blank');
    }
}

// 迭代优化
function handleIterationKeyPress(event) {
    if (event.key === 'Enter') {
        iterateCourseware();
    }
}

async function iterateCourseware() {
    const input = document.getElementById('iteration-input');
    const modification = input.value.trim();
    
    if (!modification) return;
    
    showLoading();
    
    try {
        const response = await fetch('/api/iterate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                modification: modification,
                current_intent: currentIntent
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addMessageToChat('assistant', '✅ 课件已根据您的意见更新！请查看"课件预览"标签页。');
            
            // 更新生成的文件
            generatedFiles = {
                ppt: data.ppt_path,
                word: data.word_path,
                game: data.game_path
            };
            
            // 更新当前意图
            if (data.updated_intent) {
                currentIntent = data.updated_intent;
            }
            
            // 更新预览
            updatePreview(data);
            
            // 清空输入框
            input.value = '';
        } else {
            addMessageToChat('assistant', '❌ 更新失败：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('assistant', '❌ 更新时出现网络错误，请稍后重试。');
    }
    
    hideLoading();
}

// 知识库上传
async function handleKBUpload(event) {
    const files = event.target.files;
    
    if (files.length === 0) return;
    
    showLoading();
    
    // 显示上传进度
    const progressBar = document.getElementById('kb-upload-progress');
    const progressText = document.getElementById('kb-upload-text');
    progressBar.style.display = 'block';
    progressText.textContent = '正在解析文档...';
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        const response = await fetch('/api/knowledge/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            progressText.textContent = '正在分块入库...';
            
            // 显示上传详情
            let uploadDetails = `成功上传 ${data.count} 个文档到知识库\n`;
            data.uploaded_files.forEach(file => {
                uploadDetails += `- ${file.filename}: 提取${file.text_length}字符，分块${file.chunks}个，入库${file.added}个\n`;
            });
            uploadDetails += `总入库块数: ${data.total_chunks}`;
            
            alert(uploadDetails);
            updateKnowledgeStats();
            updateKnowledgeDocumentList(data.stats);
        } else {
            alert('上传失败：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('上传时出现网络错误');
    }
    
    hideLoading();
    progressBar.style.display = 'none';
}

// 更新知识库统计
async function updateKnowledgeStats() {
    try {
        const response = await fetch('/api/knowledge/stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('kb-count').textContent = data.stats.total_documents;
            updateKnowledgeDocumentList(data.stats);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// 更新知识库文档列表
function updateKnowledgeDocumentList(stats) {
    const container = document.getElementById('kb-documents');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!stats.documents || stats.documents.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">暂无文档</p>';
        return;
    }
    
    stats.documents.forEach(docName => {
        const docDiv = document.createElement('div');
        docDiv.className = 'kb-document-item';
        docDiv.innerHTML = `
            <span class="doc-name">📄 ${docName}</span>
            <span class="doc-chunks">${stats.doc_stats[docName]} 块</span>
            <button class="delete-doc-btn" onclick="deleteDocument('${docName}')">删除</button>
        `;
        container.appendChild(docDiv);
    });
}

// 删除文档
async function deleteDocument(sourceName) {
    if (!confirm(`确定要删除文档 "${sourceName}" 吗？`)) return;
    
    showLoading();
    
    try {
        const response = await fetch('/api/knowledge/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ source_name: sourceName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`成功删除 ${data.deleted_count} 个文本块`);
            updateKnowledgeStats();
        } else {
            alert('删除失败：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('删除时出现网络错误');
    }
    
    hideLoading();
}

// 清空知识库
async function clearKnowledgeBase() {
    if (!confirm('确定要清空知识库吗？这将删除所有文档和文本块！')) return;
    
    showLoading();
    
    try {
        const response = await fetch('/api/knowledge/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`成功清空知识库，删除了 ${data.deleted_count} 个文本块`);
            updateKnowledgeStats();
        } else {
            alert('清空失败：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('清空时出现网络错误');
    }
    
    hideLoading();
}

// 知识库搜索
function handleKBSearch(event) {
    if (event.key === 'Enter') {
        searchKnowledgeBase();
    }
}

async function searchKnowledgeBase() {
    const query = document.getElementById('kb-search-input').value.trim();
    
    if (!query) return;
    
    showLoading();
    
    try {
        const response = await fetch('/api/knowledge/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displaySearchResults(data.results);
        } else {
            alert('搜索失败：' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('搜索时出现网络错误');
    }
    
    hideLoading();
}

// 显示搜索结果
function displaySearchResults(results) {
    const container = document.getElementById('knowledge-results');
    container.innerHTML = '';
    
    if (results.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">未找到相关内容</p>';
        return;
    }
    
    results.forEach(result => {
        const item = document.createElement('div');
        item.className = 'knowledge-item';
        
        // 获取来源文档名称
        const sourceName = result.metadata?.source || '未知文档';
        
        // 相似度
        const similarity = result.similarity || (1 - result.distance);
        const similarityPercent = (similarity * 100).toFixed(1);
        
        // 低相似度警告
        const lowSimilarityWarning = result.is_low_similarity ? 
            '<span class="low-similarity-warning">【匹配度较低】</span>' : '';
        
        item.innerHTML = `
            <div class="knowledge-header">
                <span class="source-name">📄 ${sourceName}</span>
                <span class="similarity-score">相似度: ${similarityPercent}%</span>
            </div>
            <div class="knowledge-preview">${result.preview || result.content.substring(0, 100) + '...'}</div>
            <div class="knowledge-content">${result.content}</div>
            ${lowSimilarityWarning}
        `;
        container.appendChild(item);
    });
}

// 显示加载提示
function showLoading() {
    document.getElementById('loading-overlay').style.display = 'flex';
}

// 隐藏加载提示
function hideLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// 页面加载时初始化
window.onload = function() {
    updateKnowledgeStats();
};
