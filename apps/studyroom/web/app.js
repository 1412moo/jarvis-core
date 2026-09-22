// Jarvis Studyroom v0.1 Foundation Client
(function () {
  'use strict';

  const API_ENDPOINTS = {
    recordroom: '/content/recordroom.json',
    technologies: '/content/technologies.json',
    features: '/content/features.json',
    glossary: '/content/glossary.json',
    learn: '/content/learn.json'
  };

  const state = {
    currentTab: 'home',
    cache: {}
  };

  const appView = document.getElementById('app-view');
  const navTabs = document.querySelectorAll('.nav-tab');

  // Helper: Fetch JSON with in-memory caching
  async function loadData(key) {
    if (state.cache[key]) {
      return state.cache[key];
    }
    const endpoint = API_ENDPOINTS[key];
    if (!endpoint) return null;

    try {
      const res = await fetch(endpoint);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to load ${endpoint}`);
      }
      const data = await res.json();
      state.cache[key] = data;
      return data;
    } catch (err) {
      console.error(`[Studyroom] Error loading ${key}:`, err);
      return null;
    }
  }

  // Helper: Safe text escaping
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // 1. Home View
  function renderHome() {
    appView.innerHTML = `
      <div class="view-header">
        <h2>Home: 학습 개요</h2>
        <p>Jarvis-Core 프로젝트 자체를 살아있는 교재로 삼아 소프트웨어 아키텍처를 학습합니다.</p>
      </div>

      <div class="hero-box">
        <h2>Studyroom의 목적</h2>
        <p>이곳은 Jarvis-Core를 운영하거나 제어하는 콘솔이 아닙니다. 저장소의 역사, 설계 원칙, 에이전트 오케스트레이션, 방어적 엔지니어링 패턴을 학습자가 스스로 이해하고 복습할 수 있도록 정리한 <strong>Read-Only 학습 전용 공간</strong>입니다.</p>
        <p>Studyroom은 완전히 격리되어 작동하며, 프로젝트의 원본 사실(Git History, Task Records)을 사람이 이해하기 쉬운 지식으로 전달합니다.</p>
        
        <div class="feature-summary">
          <div class="stat-box">
            <div class="stat-num">Read-Only</div>
            <div class="stat-label">코어 런타임 무변경 격리</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">Local-First</div>
            <div class="stat-label">외부 의존성 제로 (Stdlib)</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">6 Sections</div>
            <div class="stat-label">체계화된 학습 트랙</div>
          </div>
        </div>
      </div>

      <div class="cards-grid">
        <div class="card">
          <div class="card-title">Recordroom <span class="badge">개발 역사</span></div>
          <p class="card-body">단순 Git 로그가 아닌, 사건의 발생 이유, 직면한 문제, 해결책과 엔지니어링 교훈을 정리한 역사책입니다.</p>
        </div>
        <div class="card">
          <div class="card-title">Technologies <span class="badge">기술 스택</span></div>
          <p class="card-body">Python 표준 라이브러리, Git Plumbing, Nostr Relay 등 Jarvis에서 실제로 사용하는 기술과 역할을 배웁니다.</p>
        </div>
        <div class="card">
          <div class="card-title">Features <span class="badge">핵심 기능</span></div>
          <p class="card-body">Task 수명주기, 단일 원자 쓰기, 감사 해시체인 등 Jarvis 시스템의 불변식을 분석합니다.</p>
        </div>
        <div class="card">
          <div class="card-title">Glossary <span class="badge">용어 사전</span></div>
          <p class="card-body">개발자 정의, 비개발자용 쉬운 비유, Jarvis 실제 적용 사례로 이어지는 3단 용어집입니다.</p>
        </div>
        <div class="card">
          <div class="card-title">Learn <span class="badge">실전 퀴즈</span></div>
          <p class="card-body">핵심 개념을 복습하고 객관식 퀴즈를 풀며 LocalStorage에 진도율을 저장합니다.</p>
        </div>
      </div>
    `;
  }

  // 2. Recordroom View
  async function renderRecordroom() {
    appView.innerHTML = '<div class="loading">개발 역사를 불러오는 중입니다...</div>';
    const records = await loadData('recordroom');

    if (!records || records.length === 0) {
      appView.innerHTML = '<div class="view-header"><h2>Recordroom</h2><p>기록이 없습니다.</p></div>';
      return;
    }

    const cardsHtml = records.map(rec => `
      <div class="card" style="margin-bottom: 1.25rem;">
        <div class="card-title">
          <span>${escapeHtml(rec.title)}</span>
          <span class="badge">${escapeHtml(rec.date)} &bull; ${escapeHtml(rec.task_id)}</span>
        </div>
        <div class="card-body">
          <div style="margin-bottom: 0.5rem;"><strong>무슨 일인가:</strong> ${escapeHtml(rec.what_happened)}</div>
          <div style="margin-bottom: 0.5rem;"><strong>왜 필요한가:</strong> ${escapeHtml(rec.why_needed)}</div>
          <div style="margin-bottom: 0.5rem;"><strong>어떤 문제가 있었나:</strong> ${escapeHtml(rec.issue_faced)}</div>
          <div style="margin-bottom: 0.5rem;"><strong>어떻게 해결했나:</strong> ${escapeHtml(rec.resolution)}</div>
          <div class="card-section">
            <div class="card-section-title">배운 점 (Engineering Lesson)</div>
            <p><strong>${escapeHtml(rec.engineering_lesson)}</strong></p>
          </div>
          ${rec.related_links && rec.related_links.length > 0 ? `
            <div class="card-section">
              <div class="card-section-title">관련 링크</div>
              <ul style="padding-left: 1.25rem; font-size: 0.85rem;">
                ${rec.related_links.map(link => `<li><code>${escapeHtml(link.path)}</code> (${escapeHtml(link.label)})</li>`).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      </div>
    `).join('');

    appView.innerHTML = `
      <div class="view-header">
        <h2>Recordroom: 개발 역사 기록</h2>
        <p>Jarvis-Core 개발 과정의 실제 사건과 트레이드오프, 엔지니어링 교훈을 복습합니다.</p>
      </div>
      <div>${cardsHtml}</div>
    `;
  }

  // 3. Technologies View
  async function renderTechnologies() {
    appView.innerHTML = '<div class="loading">기술 목록을 불러오는 중입니다...</div>';
    const list = await loadData('technologies');

    if (!list || list.length === 0) {
      appView.innerHTML = '<div class="view-header"><h2>Technologies</h2><p>데이터가 없습니다.</p></div>';
      return;
    }

    const cardsHtml = list.map(item => `
      <div class="card">
        <div class="card-title">${escapeHtml(item.name)}</div>
        <div class="card-body">
          <p style="margin-bottom: 0.75rem;">${escapeHtml(item.description)}</p>
          <div class="card-section">
            <div class="card-section-title">Jarvis에서의 활용</div>
            <p>${escapeHtml(item.jarvis_usage)}</p>
          </div>
        </div>
      </div>
    `).join('');

    appView.innerHTML = `
      <div class="view-header">
        <h2>Technologies: 사용 기술 스택</h2>
        <p>프로젝트에서 실제로 사용하는 기술과 표준 라이브러리 철학을 학습합니다.</p>
      </div>
      <div class="cards-grid">${cardsHtml}</div>
    `;
  }

  // 4. Features View
  async function renderFeatures() {
    appView.innerHTML = '<div class="loading">기능 목록을 불러오는 중입니다...</div>';
    const list = await loadData('features');

    if (!list || list.length === 0) {
      appView.innerHTML = '<div class="view-header"><h2>Features</h2><p>데이터가 없습니다.</p></div>';
      return;
    }

    const cardsHtml = list.map(item => `
      <div class="card">
        <div class="card-title">${escapeHtml(item.name)}</div>
        <div class="card-body">
          <div style="margin-bottom: 0.5rem;"><strong>무엇인가:</strong> ${escapeHtml(item.what)}</div>
          <div style="margin-bottom: 0.5rem;"><strong>왜 만들었는가:</strong> ${escapeHtml(item.why)}</div>
          <div style="margin-bottom: 0.5rem;"><strong>동작 방식:</strong> ${escapeHtml(item.how)}</div>
          ${item.related_tasks && item.related_tasks.length > 0 ? `
            <div class="card-section">
              <div class="card-section-title">관련 Tasks</div>
              <p><code>${item.related_tasks.map(escapeHtml).join(', ')}</code></p>
            </div>
          ` : ''}
        </div>
      </div>
    `).join('');

    appView.innerHTML = `
      <div class="view-header">
        <h2>Features: 주요 기능과 역할</h2>
        <p>Jarvis-Core를 구성하는 핵심 컴포넌트와 불변식을 확인합니다.</p>
      </div>
      <div class="cards-grid">${cardsHtml}</div>
    `;
  }

  // 5. Glossary View
  async function renderGlossary() {
    appView.innerHTML = '<div class="loading">용어 사전을 불러오는 중입니다...</div>';
    const list = await loadData('glossary');

    if (!list || list.length === 0) {
      appView.innerHTML = '<div class="view-header"><h2>Glossary</h2><p>데이터가 없습니다.</p></div>';
      return;
    }

    const cardsHtml = list.map(item => `
      <div class="card glossary-card">
        <div class="card-title">${escapeHtml(item.term)}</div>
        <div class="glossary-dev">
          <strong>1. 개발자 정의</strong>
          <p>${escapeHtml(item.dev_definition)}</p>
        </div>
        <div class="glossary-simple">
          <strong>2. 아주 쉬운 비유</strong>
          <p>${escapeHtml(item.simple_explanation)}</p>
        </div>
        <div class="glossary-example">
          <strong>3. Jarvis 실제 사례</strong>
          <p>${escapeHtml(item.jarvis_example)}</p>
        </div>
      </div>
    `).join('');

    appView.innerHTML = `
      <div class="view-header">
        <h2>Glossary: 실전 개발 용어 사전</h2>
        <p>개발자 정의, 쉬운 비유, Jarvis 실제 적용 사례로 이어지는 3단계 용어집입니다.</p>
      </div>
      <div class="cards-grid">${cardsHtml}</div>
    `;
  }

  // 6. Learn View & Quiz
  async function renderLearn() {
    appView.innerHTML = '<div class="loading">학습 모듈을 불러오는 중입니다...</div>';
    const topics = await loadData('learn');

    if (!topics || topics.length === 0) {
      appView.innerHTML = '<div class="view-header"><h2>Learn</h2><p>학습 데이터가 없습니다.</p></div>';
      return;
    }

    // LocalStorage stats
    let totalQuizzes = 0;
    let solvedQuizzes = 0;

    topics.forEach(t => {
      if (t.quiz) {
        totalQuizzes += t.quiz.length;
        t.quiz.forEach((q, qIdx) => {
          const key = `studyroom_quiz_${t.id}_${qIdx}`;
          const saved = localStorage.getItem(key);
          if (saved) {
            try {
              const parsed = JSON.parse(saved);
              if (parsed.isCorrect) solvedQuizzes++;
            } catch (e) {}
          }
        });
      }
    });

    const progressPct = totalQuizzes > 0 ? Math.round((solvedQuizzes / totalQuizzes) * 100) : 0;

    const cardsHtml = topics.map(topic => {
      const quizHtml = (topic.quiz || []).map((q, qIdx) => {
        const quizStorageKey = `studyroom_quiz_${topic.id}_${qIdx}`;
        let savedState = null;
        try {
          savedState = JSON.parse(localStorage.getItem(quizStorageKey) || 'null');
        } catch (e) {}

        const isSolved = savedState && savedState.isCorrect;
        const selectedIdx = savedState ? savedState.selected : -1;

        const optionsHtml = q.options.map((opt, oIdx) => {
          let extraClass = '';
          if (savedState) {
            if (oIdx === q.answer) {
              extraClass = 'correct';
            } else if (oIdx === selectedIdx) {
              extraClass = 'incorrect';
            }
          }
          return `
            <button 
              class="quiz-btn ${extraClass}" 
              data-topic-id="${escapeHtml(topic.id)}" 
              data-quiz-idx="${qIdx}" 
              data-opt-idx="${oIdx}"
              ${savedState ? 'disabled' : ''}
            >
              ${oIdx + 1}. ${escapeHtml(opt)}
            </button>
          `;
        }).join('');

        let feedbackClass = '';
        let feedbackText = '';
        if (savedState) {
          if (savedState.isCorrect) {
            feedbackClass = 'show-correct';
            feedbackText = '🎉 정답입니다! (LocalStorage에 저장됨)';
          } else {
            feedbackClass = 'show-incorrect';
            feedbackText = '❌ 오답입니다. 다시 시도해 보세요.';
          }
        }

        return `
          <div class="quiz-box" id="quiz-${escapeHtml(topic.id)}-${qIdx}">
            <div class="quiz-question">Q${qIdx + 1}. ${escapeHtml(q.question)}</div>
            <div class="quiz-options">${optionsHtml}</div>
            <div class="quiz-feedback ${feedbackClass}" id="feedback-${escapeHtml(topic.id)}-${qIdx}">${feedbackText}</div>
          </div>
        `;
      }).join('');

      return `
        <div class="learn-card">
          <div class="card-title">${escapeHtml(topic.title)}</div>
          <div style="margin-bottom: 0.75rem;">
            <strong>개발자 관점:</strong>
            <p style="color: var(--text-muted);">${escapeHtml(topic.developer_explanation)}</p>
          </div>
          <div style="margin-bottom: 0.75rem;">
            <strong>초보자 관점:</strong>
            <p style="color: var(--text-muted);">${escapeHtml(topic.beginner_explanation)}</p>
          </div>
          <div style="margin-bottom: 0.75rem;">
            <strong>Jarvis 실제 사례:</strong>
            <p style="color: var(--text-muted);">${escapeHtml(topic.jarvis_example)}</p>
          </div>
          ${quizHtml}
        </div>
      `;
    }).join('');

    appView.innerHTML = `
      <div class="view-header">
        <h2>Learn: 실전 개념과 퀴즈</h2>
        <p>Jarvis-Core의 설계 원리를 퀴즈로 풀고 진행률을 로컬 브라우저에 저장합니다.</p>
      </div>
      <div class="progress-banner">
        <span>퀴즈 진행률: <strong>${solvedQuizzes} / ${totalQuizzes} 완료 (${progressPct}%)</strong></span>
        <button id="reset-progress-btn" style="background: none; border: 1px solid var(--card-border); color: var(--text-muted); padding: 0.25rem 0.5rem; border-radius: 4px; cursor: pointer;">진행률 초기화</button>
      </div>
      <div class="learn-container">${cardsHtml}</div>
    `;

    // Attach quiz click events
    appView.querySelectorAll('.quiz-btn').forEach(btn => {
      btn.addEventListener('click', handleQuizClick);
    });

    // Reset progress button
    const resetBtn = document.getElementById('reset-progress-btn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        if (confirm('모든 퀴즈 풀이 기록을 초기화하시겠습니까?')) {
          topics.forEach(t => {
            if (t.quiz) {
              t.quiz.forEach((_, qIdx) => {
                localStorage.removeItem(`studyroom_quiz_${t.id}_${qIdx}`);
              });
            }
          });
          renderLearn();
        }
      });
    }
  }

  // Quiz Click Handler
  async function handleQuizClick(e) {
    const btn = e.currentTarget;
    const topicId = btn.dataset.topicId;
    const qIdx = parseInt(btn.dataset.quizIdx, 10);
    const selectedOpt = parseInt(btn.dataset.optIdx, 10);

    const topics = await loadData('learn');
    if (!topics) return;

    const topic = topics.find(t => t.id === topicId);
    if (!topic || !topic.quiz || !topic.quiz[qIdx]) return;

    const quiz = topic.quiz[qIdx];
    const isCorrect = (selectedOpt === quiz.answer);

    const storageKey = `studyroom_quiz_${topicId}_${qIdx}`;
    localStorage.setItem(storageKey, JSON.stringify({
      answered: true,
      selected: selectedOpt,
      isCorrect: isCorrect
    }));

    // Re-render Learn view to reflect new state & update progress banner
    renderLearn();
  }

  // Navigation Switch
  function switchTab(tab) {
    state.currentTab = tab;
    navTabs.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    switch (tab) {
      case 'home':
        renderHome();
        break;
      case 'recordroom':
        renderRecordroom();
        break;
      case 'technologies':
        renderTechnologies();
        break;
      case 'features':
        renderFeatures();
        break;
      case 'glossary':
        renderGlossary();
        break;
      case 'learn':
        renderLearn();
        break;
      default:
        renderHome();
    }
  }

  // Initialize
  navTabs.forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tab);
    });
  });

  // Default view
  switchTab('home');
})();
