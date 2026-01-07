/**
 * Google Tag Manager & GA4 Analytics
 *
 * 간단한 이벤트 추적 헬퍼
 * GTM을 통해 GA4로 이벤트 전송 → BigQuery 자동 export
 */

// GTM dataLayer 선언
declare global {
  interface Window {
    dataLayer: any[];
  }
}

/**
 * GTM 이벤트 전송
 */
export const trackEvent = (
  eventName: string,
  eventParams?: Record<string, any>
) => {
  if (typeof window === 'undefined' || !window.dataLayer) {
    console.warn('GTM not initialized');
    return;
  }

  window.dataLayer.push({
    event: eventName,
    ...eventParams
  });

  console.log('📊 Event tracked:', eventName, eventParams);
};

/**
 * 페이지뷰 추적
 */
export const trackPageView = (pagePath: string, pageTitle?: string) => {
  trackEvent('page_view', {
    page_path: pagePath,
    page_title: pageTitle || document.title
  });
};

/**
 * Agent 대화 시작
 */
export const trackAgentChatStart = (agentType: string) => {
  trackEvent('agent_chat_start', {
    agent_type: agentType,
    timestamp: Date.now()
  });
};

/**
 * Agent 쿼리 전송
 */
export const trackAgentQuery = (
  agentType: string,
  queryLength: number
) => {
  trackEvent('agent_query', {
    agent_type: agentType,
    query_length: queryLength
  });
};

/**
 * Agent 응답 받음
 */
export const trackAgentResponse = (
  agentType: string,
  responseTime: number,
  success: boolean
) => {
  trackEvent('agent_response', {
    agent_type: agentType,
    response_time_ms: responseTime,
    success: success
  });
};

/**
 * 전환 이벤트 (예: 구독 시작)
 */
export const trackConversion = (
  conversionType: string,
  value?: number
) => {
  trackEvent(conversionType, {
    value: value || 0,
    currency: 'USD'
  });
};

export default {
  trackEvent,
  trackPageView,
  trackAgentChatStart,
  trackAgentQuery,
  trackAgentResponse,
  trackConversion
};
