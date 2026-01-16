import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import json
import re

# 페이지 설정
st.set_page_config(
    page_title="AI 학습 멘토",
    page_icon="📚",
    layout="wide"
)

# API 키 설정
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("⚠️ API 키를 설정해주세요. Streamlit Secrets에 GEMINI_API_KEY를 추가하세요.")
    st.stop()

# 세션 상태 초기화
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'quiz_submitted' not in st.session_state:
    st.session_state.quiz_submitted = False

def extract_pdf_text(pdf_file):
    """PDF에서 텍스트 추출"""
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def split_text(text):
    """텍스트를 청크로 분할"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=300,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def generate_quiz(text_chunks):
    """Gemini를 사용하여 퀴즈 생성"""
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    # 텍스트 청크 결합 (토큰 제한 고려)
    combined_text = "\n\n".join(text_chunks[:3])
    
    prompt = f"""
아래 PDF 내용을 분석하여 핵심 개념을 테스트하는 객관식 퀴즈 5문제를 생성해주세요.

PDF 내용:
{combined_text}

다음 JSON 형식으로 정확히 응답해주세요:
{{
  "questions": [
    {{
      "question": "질문 내용",
      "options": ["선택지1", "선택지2", "선택지3", "선택지4"],
      "correct_answer": 0,
      "explanation": "정답 해설 (PDF 내용 기반)"
    }}
  ]
}}

규칙:
1. 정확히 5문제를 생성하세요
2. correct_answer는 0-3 사이의 인덱스입니다
3. 해설은 PDF 내용을 근거로 상세하게 작성하세요
4. JSON 형식만 출력하고 다른 텍스트는 포함하지 마세요
"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # JSON 추출 (마크다운 코드 블록 제거)
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        
        quiz_data = json.loads(response_text)
        return quiz_data
    except Exception as e:
        st.error(f"퀴즈 생성 중 오류 발생: {str(e)}")
        return None

def reset_quiz():
    """퀴즈 초기화"""
    st.session_state.quiz_data = None
    st.session_state.current_question = 0
    st.session_state.user_answers = {}
    st.session_state.score = 0
    st.session_state.quiz_submitted = False

# UI 시작
st.title("📚 AI 학습 멘토")
st.markdown("### PDF를 업로드하고 맞춤형 퀴즈로 학습하세요!")

# 사이드바
with st.sidebar:
    st.header("📁 PDF 업로드")
    uploaded_file = st.file_uploader("PDF 파일을 선택하세요", type=['pdf'])
    
    if uploaded_file is not None:
        if st.button("🎯 퀴즈 생성하기", use_container_width=True):
            with st.spinner("PDF를 분석하고 퀴즈를 생성하는 중..."):
                # PDF 텍스트 추출
                text = extract_pdf_text(uploaded_file)
                
                # 텍스트 분할
                chunks = split_text(text)
                
                # 퀴즈 생성
                quiz_data = generate_quiz(chunks)
                
                if quiz_data and 'questions' in quiz_data:
                    st.session_state.quiz_data = quiz_data
                    st.session_state.current_question = 0
                    st.session_state.user_answers = {}
                    st.session_state.score = 0
                    st.session_state.quiz_submitted = False
                    st.success("✅ 퀴즈가 생성되었습니다!")
                    st.rerun()
    
    if st.session_state.quiz_data:
        st.divider()
        st.metric("진행률", f"{len(st.session_state.user_answers)}/5")
        if st.button("🔄 새로운 퀴즈", use_container_width=True):
            reset_quiz()
            st.rerun()

# 메인 영역
if st.session_state.quiz_data is None:
    st.info("👈 왼쪽 사이드바에서 PDF를 업로드하고 퀴즈를 생성하세요.")
else:
    questions = st.session_state.quiz_data['questions']
    
    # 모든 문제를 답변했는지 확인
    if len(st.session_state.user_answers) == len(questions):
        # 결과 화면
        st.success("🎉 모든 문제를 완료했습니다!")
        
        # 점수 계산
        correct_count = sum(
            1 for q_idx, answer in st.session_state.user_answers.items()
            if answer == questions[q_idx]['correct_answer']
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 문제", len(questions))
        with col2:
            st.metric("정답 수", correct_count)
        with col3:
            score = (correct_count / len(questions)) * 100
            st.metric("점수", f"{score:.0f}점")
        
        st.divider()
        
        # 상세 결과
        st.subheader("📊 상세 결과")
        for idx, question in enumerate(questions):
            user_answer = st.session_state.user_answers.get(idx, -1)
            correct = user_answer == question['correct_answer']
            
            with st.expander(f"{'✅' if correct else '❌'} 문제 {idx + 1}: {question['question']}", expanded=not correct):
                st.write(f"**당신의 답변:** {question['options'][user_answer] if user_answer >= 0 else '미응답'}")
                st.write(f"**정답:** {question['options'][question['correct_answer']]}")
                st.info(f"**해설:** {question['explanation']}")
    
    else:
        # 현재 문제 표시
        current_q = st.session_state.current_question
        question = questions[current_q]
        
        st.subheader(f"문제 {current_q + 1} / {len(questions)}")
        st.write(f"### {question['question']}")
        
        # 폼으로 답변 제출
        with st.form(key=f"quiz_form_{current_q}"):
            selected_option = st.radio(
                "정답을 선택하세요:",
                options=range(len(question['options'])),
                format_func=lambda x: question['options'][x],
                key=f"option_{current_q}"
            )
            
            submitted = st.form_submit_button("제출하기", use_container_width=True)
            
            if submitted:
                st.session_state.user_answers[current_q] = selected_option
                
                # 정답 확인
                if selected_option == question['correct_answer']:
                    st.success("🎉 정답입니다!")
                else:
                    st.error(f"❌ 오답입니다. 정답은 '{question['options'][question['correct_answer']]}'입니다.")
                    st.info(f"**해설:** {question['explanation']}")
                
                # 다음 문제로 이동
                if current_q + 1 < len(questions):
                    if st.button("다음 문제로 →"):
                        st.session_state.current_question += 1
                        st.rerun()
                else:
                    if st.button("결과 보기"):
                        st.rerun()

# 푸터
st.divider()
st.caption("Made with ❤️ using Streamlit & Google Gemini")
```

## requirements.txt
```
streamlit==1.31.0
google-generativeai==0.3.2
PyPDF2==3.0.1
langchain==0.1.0
