import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import json
import re

st.set_page_config(page_title="AI 학습 멘토", page_icon="📚", layout="wide")

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("API 키를 설정해주세요.")
    st.stop()

if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'user_answers' not in st.session_state:
    st.session_state.user_answers = {}

def extract_pdf_text(pdf_file):
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def generate_quiz(text):
    model = genai.GenerativeModel('gemini-2.5-flash')
    if len(text) > 10000:
        text = text[:10000]
    
    prompt = "아래 PDF 내용을 분석하여 객관식 퀴즈 5문제를 JSON 형식으로 생성해주세요.\n\n"
    prompt += "PDF 내용:\n" + text + "\n\n"
    prompt += "형식:\n"
    prompt += '{"questions": [{"question": "질문", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "해설"}]}\n\n'
    prompt += "규칙: 5문제, correct_answer는 0-3, JSON만 출력"
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        quiz_data = json.loads(response_text)
        return quiz_data
    except Exception as e:
        st.error(f"오류: {str(e)}")
        return None

def reset_quiz():
    st.session_state.quiz_data = None
    st.session_state.current_question = 0
    st.session_state.user_answers = {}

st.title("📚 AI 학습 멘토")
st.markdown("### PDF를 업로드하고 맞춤형 퀴즈로 학습하세요!")

with st.sidebar:
    st.header("📁 PDF 업로드")
    uploaded_file = st.file_uploader("PDF 파일을 선택하세요", type=['pdf'])
    
    if uploaded_file:
        if st.button("🎯 퀴즈 생성하기", use_container_width=True):
            with st.spinner("퀴즈 생성 중..."):
                text = extract_pdf_text(uploaded_file)
                if text.strip():
                    quiz_data = generate_quiz(text)
                    if quiz_data and 'questions' in quiz_data:
                        st.session_state.quiz_data = quiz_data
                        st.session_state.current_question = 0
                        st.session_state.user_answers = {}
                        st.success("퀴즈 생성 완료!")
                        st.rerun()
    
    if st.session_state.quiz_data:
        st.divider()
        st.metric("진행률", f"{len(st.session_state.user_answers)}/5")
        if st.button("🔄 새로운 퀴즈", use_container_width=True):
            reset_quiz()
            st.rerun()

if st.session_state.quiz_data is None:
    st.info("왼쪽 사이드바에서 PDF를 업로드하고 퀴즈를 생성하세요.")
else:
    questions = st.session_state.quiz_data['questions']
    
    if len(st.session_state.user_answers) == len(questions):
        st.success("🎉 모든 문제를 완료했습니다!")
        
        correct_count = sum(1 for q_idx, answer in st.session_state.user_answers.items() 
                          if answer == questions[q_idx]['correct_answer'])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("총 문제", len(questions))
        col2.metric("정답 수", correct_count)
        col3.metric("점수", f"{(correct_count/len(questions)*100):.0f}점")
        
        st.divider()
        st.subheader("📊 상세 결과")
        
        for idx, question in enumerate(questions):
            user_answer = st.session_state.user_answers.get(idx, -1)
            correct = user_answer == question['correct_answer']
            
            with st.expander(f"{'✅' if correct else '❌'} 문제 {idx+1}: {question['question']}", expanded=not correct):
                st.write(f"**당신의 답변:** {question['options'][user_answer] if user_answer >= 0 else '미응답'}")
                st.write(f"**정답:** {question['options'][question['correct_answer']]}")
                st.info(f"**해설:** {question['explanation']}")
    else:
        current_q = st.session_state.current_question
        question = questions[current_q]
        
        st.subheader(f"문제 {current_q+1} / {len(questions)}")
        st.write(f"### {question['question']}")
        
        with st.form(key=f"form_{current_q}"):
            selected = st.radio("정답을 선택하세요:", 
                              options=range(len(question['options'])),
                              format_func=lambda x: question['options'][x])
            submitted = st.form_submit_button("제출하기", use_container_width=True)
        
        if submitted and current_q not in st.session_state.user_answers:
            st.session_state.user_answers[current_q] = selected
            st.rerun()
        
        if current_q in st.session_state.user_answers:
            user_answer = st.session_state.user_answers[current_q]
            
            if user_answer == question['correct_answer']:
                st.success("🎉 정답입니다!")
            else:
                st.error(f"❌ 오답입니다. 정답: {question['options'][question['correct_answer']]}")
                st.info(f"**해설:** {question['explanation']}")
            
            if current_q + 1 < len(questions):
                if st.button("다음 문제로 →", key="next", use_container_width=True):
                    st.session_state.current_question += 1
                    st.rerun()
            else:
                if st.button("결과 보기", key="result", use_container_width=True):
                    st.rerun()

st.divider()
st.caption("Made with Streamlit & Google Gemini 2.5 Flash")
