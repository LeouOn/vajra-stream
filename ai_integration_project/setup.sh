#!/bin/bash

# Vajra.Stream AI Integration Setup Script
# Installs Z AI GLM 4.6 integration with LM Studio and advanced TTS

set -e  # Exit on any error

echo "🚀 Vajra.Stream AI Integration Setup"
echo "=================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p config
mkdir -p cache/tts
mkdir -p models/tts
mkdir -p models/local
mkdir -p logs

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file..."
    cat > .env << 'EOF'
# Z AI GLM 4.6 Configuration
Z_AI_API_KEY=your_z_ai_api_key_here

# OpenAI Fallback
OPENAI_API_KEY=your_openai_api_key_here

# ElevenLabs TTS
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Anthropic Fallback
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# LM Studio Settings
LM_STUDIO_BASE_URL=http://127.0.0.1:1234
EOF
    echo "✅ Created .env file"
    echo "📝 Please edit .env file with your actual API keys"
else
    echo "✅ .env file already exists"
fi

# Create startup script
echo "🚀 Creating startup script..."
cat > start_ai_integration.sh << 'EOF'
#!/bin/bash

# Vajra.Stream AI Integration Startup Script

echo "🧘 Starting Vajra.Stream with AI Integration..."

# Check if LM Studio is running
echo "🔍 Checking LM Studio status..."
if curl -s -X GET "http://127.0.0.1:1234/v1/models" > /dev/null 2>&1; then
    echo "✅ LM Studio is running"
else
    echo "⚠️  LM Studio is not running"
    echo "Please start LM Studio and load models:"
    echo "1. Open LM Studio"
    echo "2. Go to chat tab (💬)"
    echo "3. Load models: openai_gpt-oss-120b-neo-imatrix, aquif-3.5-max-42b-a3b-i1, nvidia_qwen3-nemotron-32b-rlbff"
    echo "4. Start server"
    echo "5. Server should be running on http://127.0.0.1:1234"
fi

# Start backend server
echo "🚀 Starting backend server..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend development server
echo "🎨 Starting frontend development server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "🌟 Services starting up..."
echo ""
echo "📊 Service URLs:"
echo "   Backend API: http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
echo "   Frontend:   http://localhost:3000"
echo ""
echo "🔧 Configuration:"
echo "   AI Models: ./config/ai_models.yaml"
echo "   TTS Voices: ./config/tts_voices.yaml"
echo ""
echo "📝 Next Steps:"
echo "   1. Edit .env file with your API keys"
echo "   2. Ensure LM Studio is running with models loaded"
echo "   3. Test API endpoints: curl http://localhost:8000/api/v1/llm/model-status"
echo "   4. Open frontend: http://localhost:3000"
echo ""
echo "🛑 To stop services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "✅ AI Integration setup complete!"
EOF

chmod +x start_ai_integration.sh
echo "✅ Created startup script"
EOF

echo ""
echo "🎯 Setup Summary:"
echo "=================="
echo "✅ Virtual environment created/updated"
echo "✅ Dependencies installed"
echo "✅ Directory structure created"
echo "✅ Configuration files created"
echo "✅ Startup script created"
echo ""
echo "📋 Manual Steps Required:"
echo "1. Edit .env file with your actual API keys:"
echo "   - Z_AI_API_KEY (from Z AI)"
echo "   - OPENAI_API_KEY (for OpenAI TTS)"
echo "   - ELEVENLABS_API_KEY (for ElevenLabs TTS)"
echo "   - ANTHROPIC_API_KEY (for Anthropic fallback)"
echo ""
echo "2. Install and start LM Studio:"
echo "   - Download from https://lmstudio.ai/"
echo "   - Load models: openai_gpt-oss-120b-neo-imatrix, aquif-3.5-max-42b-a3b-i1, nvidia_qwen3-nemotron-32b-rlbff"
echo "   - Start server (should run on http://127.0.0.1:1234)"
echo ""
echo "3. Start the services:"
echo "   ./start_ai_integration.sh"
echo ""
echo "🌟 Access Points:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Documentation: http://localhost:8000/docs"
echo ""
echo "📚 For testing:"
echo "   curl -X GET http://localhost:8000/api/v1/llm/model-status"
echo "   curl -X POST http://localhost:8000/api/v1/llm/generate-prayer -H 'Content-Type: application/json' -d '{\"intention\":\"peace\",\"use_local_model\":true}'"
echo ""
echo "🎉 AI Integration setup complete!"