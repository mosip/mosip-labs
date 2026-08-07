{{/*
Resource names are fixed (not release-templated) so this chart is a drop-in
replacement for ../../k8s/*.yaml — the Rancher deployment guide, Prometheus
alert expressions, and the nexus-ui chart's same-origin /api assumption all
hardcode these names. This chart is designed for one install per cluster.
*/}}

{{- define "nexus-server.image" -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{ .Values.image.registry }}/{{ .Values.image.repository }}:{{ $tag }}
{{- end -}}

{{- define "nexus-server.imagePullPolicy" -}}
{{- .Values.image.pullPolicy | default "IfNotPresent" -}}
{{- end -}}

{{- define "nexus-server.imagePullSecrets" -}}
{{- if .Values.image.pullSecrets }}
imagePullSecrets:
  {{- range .Values.image.pullSecrets }}
  - name: {{ . }}
  {{- end }}
{{- end }}
{{- end -}}

{{- define "nexus-server.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- .Values.serviceAccount.name | default "nexus-api" -}}
{{- else -}}
{{- .Values.serviceAccount.name | default "default" -}}
{{- end -}}
{{- end -}}

{{- define "nexus-server.secretName" -}}
{{- .Values.secret.existingSecret | default "nexus-env" -}}
{{- end -}}

{{/*
Per-PVC storageClassName, falling back to the top-level default.
Usage: {{ include "nexus-server.storageClass" (dict "override" .Values.postgres.storage.storageClassName "ctx" $) }}
An override of "-" (disable dynamic provisioning) is non-empty so it always wins.
*/}}
{{- define "nexus-server.storageClass" -}}
{{- .override | default .ctx.Values.storageClassName -}}
{{- end -}}

{{/*
Standard labels, merged with commonLabels. $name is the fixed resource "app" name.
*/}}
{{- define "nexus-server.labels" -}}
app: {{ .name }}
app.kubernetes.io/part-of: mosip-nexus
app.kubernetes.io/managed-by: {{ .ctx.Release.Service }}
helm.sh/chart: {{ .ctx.Chart.Name }}-{{ .ctx.Chart.Version }}
{{- $extra := omit (.ctx.Values.commonLabels | default dict) "app" }}
{{- if $extra }}
{{ toYaml $extra }}
{{- end }}
{{- end -}}

{{- define "nexus-server.selectorLabels" -}}
app: {{ .name }}
{{- end -}}

{{- define "nexus-server.annotations" -}}
{{- if .ctx.Values.commonAnnotations }}
{{ toYaml .ctx.Values.commonAnnotations }}
{{- end }}
{{- end -}}

{{/*
Fail fast on an invalid api.routing.mode instead of silently rendering
neither ingress.yaml nor virtualservice.yaml. Call from a template that
always renders regardless of mode (service.yaml).
*/}}
{{- define "nexus-server.validateRoutingMode" -}}
{{- if not (has .Values.api.routing.mode (list "istio" "nginx")) -}}
{{ fail (printf "api.routing.mode must be \"istio\" or \"nginx\" — got %q" .Values.api.routing.mode) }}
{{- end -}}
{{- end -}}
