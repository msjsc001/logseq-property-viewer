import { getApiErrorMessage } from '../api';

export function toUserMessage(error: unknown, fallback: string): string {
  return getApiErrorMessage(error, fallback);
}
