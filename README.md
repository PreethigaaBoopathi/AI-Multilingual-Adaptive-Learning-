# TextIQ — AI-Powered Multilingual Adaptive Learning

**Transforming textbooks into personalized, interactive learning experiences with AI.**

TextIQ helps students understand complex educational material through AI-powered summaries, adaptive explanations, English–Tamil learning support, source-grounded question answering, interactive assessments, and personalized learning paths.

## 🌟 Problem Statement

Students often struggle with lengthy textbooks, complex concepts, language barriers, and limited personalized feedback. Traditional study methods do not always adapt to different learning levels or help students identify knowledge gaps.

TextIQ aims to make learning more accessible by bringing content understanding, practice, revision, and adaptive learning support together in one platform.

## 💡 Key Features

- **Intelligent Summarization:** Convert supported learning materials into concise summaries and revision notes.
- **Multimodal Ingestion:** Process supported PDF, PowerPoint, and video learning materials.
- **English and Tamil Support:** Make educational explanations more accessible to Tamil- and English-speaking learners.
- **AI Academic Tutor:** Ask questions about uploaded learning content, with source references where supported.
- **Adaptive Explanations:** Explore beginner, intermediate, and advanced explanations.
- **Concept and Prerequisite Graphs:** Visualize relationships between concepts and their dependencies.
- **Interactive Assessments:** Practice questions, receive feedback, and identify concepts that need revision.
- **Visual Learning:** Generate diagrams and flowcharts to explain complex topics.
- **Personalized Learning Paths:** Organize topics into a structured learning sequence.
- **User Authentication:** Sign up and log in to access the application.

*Feature availability depends on the current implementation and configured services.*

## 🚀 What Makes TextIQ Different?

TextIQ is designed to go beyond summarization by connecting several stages of learning:

1. Understand educational material.
2. Explore simplified explanations in a preferred language.
3. Ask questions about the source content.
4. Practice with assessments and feedback.
5. Identify related concepts and prerequisites.
6. Use available learning progress to guide further study.

The central innovation is a connected learning workflow rather than a collection of isolated AI tools.

## ⚙️ Technology Stack

The project uses the following technologies where configured in the current codebase:

- **Languages:** Python, JavaScript
- **Frontend:** React, Vite, Tailwind CSS
- **Backend:** FastAPI, Uvicorn, Pydantic
- **AI and NLP:** Google Gemini, Sarvam AI, retrieval-augmented generation (RAG), natural language processing
- **Document and Media Processing:** PyMuPDF, python-pptx, OpenCV
- **Visualization:** Mermaid.js, Recharts
- **Data and Computing:** SQLite, scikit-learn, NumPy
- **HTTP Client:** Axios

## 🏗️ System Workflow

```text
Student
   |
   v
Web Application
   |
   v
Backend API
   |
   v
Learning Material Processing
   |
   v
Content Retrieval and AI Services
   |
   +------> Summaries
   +------> Explanations
   +------> Grounded Q&A
   +------> Visualizations
   +------> Assessments
                 |
                 v
       Personalized Learning Support
```

## 💻 Getting Started

### Prerequisites

Install the tools required by your environment:

- Git
- Python
- Node.js and npm
- API credentials for external AI services, if needed

### 1. Clone the Repository

```bash
git clone https://github.com/rabinesh990/AI-multilingual-adaptive-learning.git
cd AI-multilingual-adaptive-learning
```

### 2. Set Up the Backend

```bash
cd backend
python -m venv venv
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` file using the environment variables required by your application. Add real API keys only to your local environment, never to Git.

Start the backend, assuming its entry point is `main.py`:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation, if enabled, is available at:

`http://127.0.0.1:8000/docs`

### 3. Set Up the Frontend

Open a second terminal from the project root:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite in your terminal.

*Check the actual dependency files and startup scripts if your local configuration differs from these instructions.*

## 🔐 Environment and Security

- Keep `.env` files out of Git.
- Never publish API keys, passwords, JWT signing secrets, or private user data.
- Use a strong, randomly generated JWT secret in your local environment.
- Keep private databases and uploaded user documents out of public repositories unless they are intentionally sanitized for public use.

Create an `.env.example` file with placeholder values to document required settings without exposing credentials.

## 🧪 Testing

The repository includes test files covering several learning innovations. Run the relevant tests from the project root, for example:

```bash
python test_e2e.py
python test_multimodal_innovation.py
python test_concept_graph_innovation.py
python test_tutor_innovation.py
python test_assessment_innovation.py
python test_visual_learning_paths_innovation.py
python test_adaptive_explanation_innovation6.py
```

These commands assume the test files and their dependencies are present. Run the tests and document the actual results before claiming that all tests pass.

## 🌍 Expected Impact

TextIQ aims to:

- Reduce the time required to review lengthy study materials.
- Make difficult concepts easier to understand.
- Improve access to educational content in English and Tamil.
- Encourage active learning through practice and feedback.
- Help students identify topics that need further attention.
- Support more structured and personalized study.

## 🔮 Future Enhancements

- Support for additional Indian languages.
- More advanced processing of educational videos and presentations.
- Richer visual explanations and interactive diagrams.
- More accurate mastery tracking and revision recommendations.
- Accessibility improvements and learning management system integration.

## 👥 Project Information

- **Project:** TextIQ — AI-Powered Multilingual Adaptive Learning
- **Institution:** Bannari Amman Institute of Technology
- **Department:** Artificial Intelligence and Data Science
- **Contributor:** Rabinesh

## 🎥 Demo

Add screenshots of the actual application or a link to a demo video here.

## 📄 License

Add a license file and specify the license here before distributing the project publicly.

---

**TextIQ — Making learning more understandable, inclusive, and personalized through AI.**