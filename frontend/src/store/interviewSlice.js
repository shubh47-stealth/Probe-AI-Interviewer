import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  step: 'setup', // 'setup' | 'interview' | 'report'
  sessionId: null,
  syllabus: [],
  currentTopicIdx: 0,
  probeCount: 0,
  indexedRepoFiles: [],
  messages: [],
  latestTelemetry: null,
  reportData: null,
  showXRay: true,
  loading: false,
  error: null,
};

const interviewSlice = createSlice({
  name: 'interview',
  initialState,
  reducers: {
    setLoading: (state, action) => {
      state.loading = action.payload;
      if (action.payload) state.error = null;
    },
    setError: (state, action) => {
      state.error = action.payload;
      state.loading = false;
    },
    sessionInitialized: (state, action) => {
      const { session_id, syllabus, current_topic_idx, indexed_repo_files, question } = action.payload;
      state.sessionId = session_id;
      state.syllabus = syllabus;
      state.currentTopicIdx = current_topic_idx;
      state.indexedRepoFiles = indexed_repo_files || [];
      state.probeCount = 0;
      state.messages = [{ sender: 'ai', text: question }];
      state.latestTelemetry = null;
      state.step = 'interview';
      state.loading = false;
    },
    addUserMessage: (state, action) => {
      state.messages.push({ sender: 'user', text: action.payload });
    },
    turnCompleted: (state, action) => {
      const { current_topic_idx, probe_count, next_question, xray_telemetry, is_complete } = action.payload;
      state.currentTopicIdx = current_topic_idx;
      state.probeCount = probe_count;
      state.latestTelemetry = xray_telemetry;
      if (!is_complete && next_question) {
        state.messages.push({ sender: 'ai', text: next_question });
      }
      state.loading = false;
    },
    reportLoaded: (state, action) => {
      state.reportData = action.payload;
      state.step = 'report';
      state.loading = false;
    },
    toggleXRay: (state) => {
      state.showXRay = !state.showXRay;
    },
    resetSession: () => initialState,
  },
});

export const {
  setLoading,
  setError,
  sessionInitialized,
  addUserMessage,
  turnCompleted,
  reportLoaded,
  toggleXRay,
  resetSession,
} = interviewSlice.actions;

export default interviewSlice.reducer;