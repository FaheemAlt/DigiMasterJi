/**
 * WebLLM Offline Service
 * =======================
 * Provides true offline LLM capability using WebLLM (runs model in browser via WebGPU).
 * 
 * This service:
 * 1. Downloads and caches a small LLM model for offline use
 * 2. Detects when device loses ALL internet connectivity
 * 3. Generates responses entirely in the browser
 * 
 * DigiMasterJi - Multilingual AI Tutor for Rural Education
 */

import * as webllm from '@mlc-ai/web-llm';

// Configuration for the offline model
// Using a small model optimized for chat that runs well on WebGPU
const OFFLINE_MODEL = 'gemma-2b-it-q4f32_1-MLC';

// Alternative smaller models if the main one doesn't work:
// - 'TinyLlama-1.1B-Chat-v1.0-q4f32_1-MLC' (~0.5GB)
// - 'RedPajama-INCITE-Chat-3B-v1-q4f32_1-MLC' (~1.5GB)

class WebLLMService {
    constructor() {
        this.engine = null;
        this.isInitialized = false;
        this.isLoading = false;
        this.loadProgress = 0;
        this.error = null;
        this.modelId = OFFLINE_MODEL;
        this.listeners = new Set();
    }

    /**
     * Subscribe to state changes
     * @param {Function} listener - Callback function
     * @returns {Function} Unsubscribe function
     */
    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    /**
     * Notify all listeners of state change
     */
    _notifyListeners() {
        const state = this.getState();
        this.listeners.forEach(listener => listener(state));
    }

    /**
     * Get current service state
     */
    getState() {
        return {
            isInitialized: this.isInitialized,
            isLoading: this.isLoading,
            loadProgress: this.loadProgress,
            error: this.error,
            modelId: this.modelId,
            isSupported: this.isWebGPUSupported(),
        };
    }

    /**
     * Check if WebGPU is supported on this device
     * @returns {boolean}
     */
    isWebGPUSupported() {
        if (typeof navigator === 'undefined') return false;
        return 'gpu' in navigator;
    }

    /**
     * Check if the model is already cached in IndexedDB
     * Note: This is a best-effort check as WebLLM API may vary
     * @returns {Promise<boolean>}
     */
    async isModelCached() {
        try {
            // WebLLM may not have this function in all versions
            if (typeof webllm.hasModelInCache === 'function') {
                const hasCache = await webllm.hasModelInCache(this.modelId);
                return hasCache;
            }
            // Fallback: assume not cached if function doesn't exist
            return false;
        } catch (error) {
            console.warn('[WebLLM] Error checking cache:', error);
            return false;
        }
    }

    /**
     * Initialize the WebLLM engine (downloads model if not cached)
     * @param {Function} onProgress - Optional progress callback
     * @returns {Promise<boolean>}
     */
    async initialize(onProgress = null) {
        if (this.isInitialized) {
            console.log('[WebLLM] Already initialized');
            return true;
        }

        if (this.isLoading) {
            console.log('[WebLLM] Already loading');
            return false;
        }

        if (!this.isWebGPUSupported()) {
            this.error = 'WebGPU is not supported on this device. Offline mode is unavailable.';
            this._notifyListeners();
            return false;
        }

        this.isLoading = true;
        this.error = null;
        this.loadProgress = 0;
        this._notifyListeners();

        try {
            console.log('[WebLLM] Initializing engine with model:', this.modelId);

            // Create engine with progress callback
            this.engine = await webllm.CreateMLCEngine(this.modelId, {
                initProgressCallback: (progress) => {
                    this.loadProgress = progress.progress || 0;
                    this._notifyListeners();

                    // Call custom progress callback if provided
                    if (onProgress) {
                        onProgress({
                            progress: this.loadProgress,
                            text: progress.text || '',
                            timeElapsed: progress.timeElapsed || 0,
                        });
                    }

                    console.log(`[WebLLM] Loading: ${(this.loadProgress * 100).toFixed(1)}% - ${progress.text || ''}`);
                },
            });

            this.isInitialized = true;
            this.isLoading = false;
            this.loadProgress = 1;
            this._notifyListeners();

            console.log('[WebLLM] Engine initialized successfully');
            return true;
        } catch (error) {
            console.error('[WebLLM] Initialization error:', error);
            this.error = error.message || 'Failed to initialize offline model';
            this.isLoading = false;
            this.isInitialized = false;
            this._notifyListeners();
            return false;
        }
    }

    /**
     * Generate a response for the given message
     * @param {string} userMessage - The user's message
     * @param {Object} options - Generation options
     * @returns {Promise<string>}
     */
    async generate(userMessage, options = {}) {
        if (!this.isInitialized || !this.engine) {
            throw new Error('WebLLM engine not initialized');
        }

        const {
            systemPrompt = this._getDefaultSystemPrompt(),
            maxTokens = 512,
            temperature = 0.7,
        } = options;

        try {
            const messages = [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: userMessage },
            ];

            const response = await this.engine.chat.completions.create({
                messages,
                max_tokens: maxTokens,
                temperature,
            });

            return response.choices[0]?.message?.content || '';
        } catch (error) {
            console.error('[WebLLM] Generation error:', error);
            throw error;
        }
    }

    /**
     * Generate a streaming response
     * @param {string} userMessage - The user's message
     * @param {Object} callbacks - { onToken, onComplete, onError }
     * @param {Object} options - Generation options
     */
    async generateStream(userMessage, callbacks = {}, options = {}) {
        const { onToken, onComplete, onError } = callbacks;

        if (!this.isInitialized || !this.engine) {
            onError?.(new Error('Offline model not ready. Please wait for it to load.'));
            return;
        }

        const {
            systemPrompt = this._getDefaultSystemPrompt(),
            maxTokens = 512,
            temperature = 0.7,
        } = options;

        try {
            const messages = [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: userMessage },
            ];

            // Create streaming completion
            const chunks = await this.engine.chat.completions.create({
                messages,
                max_tokens: maxTokens,
                temperature,
                stream: true,
            });

            let fullResponse = '';

            for await (const chunk of chunks) {
                const content = chunk.choices[0]?.delta?.content || '';
                if (content) {
                    fullResponse += content;
                    onToken?.(content);
                }
            }

            onComplete?.({
                content: fullResponse,
                role: 'assistant',
                offline_mode: true,
                model: this.modelId,
            });
        } catch (error) {
            console.error('[WebLLM] Streaming error:', error);
            onError?.(error);
        }
    }

    /**
     * Get the default system prompt for DigiMasterJi
     */
    _getDefaultSystemPrompt() {
        return `You are DigiMasterJi, a friendly AI tutor helping students learn.
You are currently running in OFFLINE MODE with limited capabilities.

=== CRITICAL RESTRICTION ===
You are STRICTLY an educational AI tutor. You can ONLY help with:
- Science (Physics, Chemistry, Biology, Environmental Science)
- Technology (Computers, Programming, Digital Literacy)
- Engineering concepts and problem-solving
- Mathematics (Arithmetic, Algebra, Geometry, Calculus, Statistics)
- General educational topics (Study skills, Exam preparation, Learning strategies)

If a student asks about ANYTHING that is NOT related to education, academics, STEM, or learning, you MUST respond with:
"I'm sorry, but I'm an educational AI tutor designed to help you with your studies. I can only assist with Science, Technology, Engineering, Mathematics, and educational topics. Please feel free to ask me any question about your academics, and I'll be happy to help!"

Topics you MUST DECLINE: Entertainment, movies, personal advice, relationships, politics, jokes, games, cooking, health advice, legal/financial advice, or any inappropriate content.
=== END RESTRICTION ===

Important guidelines:
- Give brief, helpful answers
- Use simple language suitable for students
- Be encouraging and supportive
- If you're not sure about something, say so
- Keep responses concise (2-3 paragraphs max)
- Be SHORT and DIRECT - no filler phrases or verbose introductions, just answer the question

Note: You cannot access the internet or learning materials in offline mode.
Focus on helping with educational questions only.`;
    }

    /**
     * Clear the model cache to free up storage
     * Note: This may not work in all WebLLM versions
     * @returns {Promise<void>}
     */
    async clearCache() {
        try {
            // Try to delete from cache if the function exists
            if (typeof webllm.deleteModelFromCache === 'function') {
                await webllm.deleteModelFromCache(this.modelId);
            }
            // Always reset local state
            this.isInitialized = false;
            this.engine = null;
            this._notifyListeners();
            console.log('[WebLLM] Cache cleared (state reset)');
        } catch (error) {
            console.error('[WebLLM] Error clearing cache:', error);
            // Still reset local state even if cache clear fails
            this.isInitialized = false;
            this.engine = null;
            this._notifyListeners();
        }
    }

    /**
     * Get estimated model size for download
     * @returns {string}
     */
    getModelSize() {
        // Approximate sizes for common models
        const sizes = {
            'gemma-2b-it-q4f32_1-MLC': '~1.2 GB',
            'TinyLlama-1.1B-Chat-v1.0-q4f32_1-MLC': '~650 MB',
            'RedPajama-INCITE-Chat-3B-v1-q4f32_1-MLC': '~1.8 GB',
        };
        return sizes[this.modelId] || '~1 GB';
    }

    /**
     * Unload the model to free memory
     */
    async unload() {
        if (this.engine) {
            try {
                await this.engine.unload();
            } catch (error) {
                console.warn('[WebLLM] Error unloading:', error);
            }
            this.engine = null;
            this.isInitialized = false;
            this._notifyListeners();
        }
    }
}

// Singleton instance
export const webLLMService = new WebLLMService();
export default webLLMService;
