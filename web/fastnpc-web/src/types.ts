export interface CharacterItem {
  role: string;
  path: string;
  updated_at: number;
  preview?: string;
  avatar_url?: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  id?: number;
}

export interface TaskState {
  status: 'pending' | 'running' | 'done' | 'error' | 'not_found' | 'cancelled';
  progress?: number;
  message?: string;
  role?: string;
  started_at?: number;
  elapsed_sec?: number;
}


export interface AdminUser {
  id: number;
  username: string;
  created_at: number;
  is_admin: number;
}

export interface AdminCharacter {
  id: number;
  name: string;
  model?: string;
  source?: string;
  created_at: number;
  updated_at: number;
  structured_json?: string;
}

export interface GroupItem {
  id: number;
  name: string;
  created_at: number;
  updated_at: number;
  member_count?: number;
}

export interface GroupMessage {
  id?: number;
  sender_type: 'user' | 'character' | 'moderator';
  sender_id?: number;
  sender_name: string;
  content: string;
  created_at?: number;
}

export interface GroupMember {
  member_type: 'user' | 'character';
  member_id?: number;
  member_name: string;
}

export interface MemberBrief {
  name: string;  // 显示名称（去掉时间戳后缀）
  original_name: string;  // 原始名称（带时间戳，用于API调用）
  type: 'user' | 'character';
  brief: string;
}

export interface Feedback {
  id: number;
  user_id: number;
  username: string;
  title: string;
  content: string;
  attachments?: string;
  status: 'pending' | 'in_progress' | 'resolved' | 'rejected';
  admin_reply?: string;
  created_at: number;
  updated_at: number;
}

