export interface CharacterItem {
  role: string;
  path: string;
  updated_at: number;
  preview?: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  id?: number;
}

export interface TaskState {
  status: 'pending' | 'running' | 'done' | 'error' | 'not_found';
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
}

export interface GroupMessage {
  id?: number;
  sender_type: 'user' | 'character';
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
  name: string;
  type: 'user' | 'character';
  brief: string;
}

