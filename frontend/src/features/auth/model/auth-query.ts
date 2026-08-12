import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchCurrentUser,
  logoutCurrentUser,
  updateCurrentUser,
  type CurrentUser,
  type UpdateCurrentUserInput,
} from "@/features/auth/api/auth-api";

export const currentUserQueryKey = ["auth", "current-user"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: fetchCurrentUser,
    retry: false,
    refetchOnWindowFocus: true,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: logoutCurrentUser,
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: currentUserQueryKey });
      queryClient.setQueryData<CurrentUser | null>(currentUserQueryKey, null);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: currentUserQueryKey });
    },
  });
}

export function useUpdateCurrentUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: UpdateCurrentUserInput) => updateCurrentUser(input),
    onSuccess: (user) => {
      queryClient.setQueryData<CurrentUser | null>(currentUserQueryKey, user);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: currentUserQueryKey });
    },
  });
}
