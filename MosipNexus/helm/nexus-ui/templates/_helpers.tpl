{{/*
Resource names are fixed (not release-templated) — matches ../../k8s/*.yaml
and the nexus-server chart's convention. Designed for one install per cluster.
*/}}

{{- define "nexus-ui.image" -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{ .Values.image.registry }}/{{ .Values.image.repository }}:{{ $tag }}
{{- end -}}

{{- define "nexus-ui.imagePullPolicy" -}}
{{- .Values.image.pullPolicy | default "IfNotPresent" -}}
{{- end -}}

{{- define "nexus-ui.imagePullSecrets" -}}
{{- if .Values.image.pullSecrets }}
imagePullSecrets:
  {{- range .Values.image.pullSecrets }}
  - name: {{ . }}
  {{- end }}
{{- end }}
{{- end -}}

{{- define "nexus-ui.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- .Values.serviceAccount.name | default "nexus-ui" -}}
{{- else -}}
{{- .Values.serviceAccount.name | default "default" -}}
{{- end -}}
{{- end -}}

{{- define "nexus-ui.labels" -}}
app: nexus-ui
app.kubernetes.io/part-of: mosip-nexus
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- $extra := omit (.Values.commonLabels | default dict) "app" }}
{{- if $extra }}
{{ toYaml $extra }}
{{- end }}
{{- end -}}

{{- define "nexus-ui.selectorLabels" -}}
app: nexus-ui
{{- end -}}

{{- define "nexus-ui.annotations" -}}
{{- if .Values.commonAnnotations }}
{{ toYaml .Values.commonAnnotations }}
{{- end }}
{{- end -}}

{{/*
Fail fast on an invalid routing.mode instead of silently rendering neither
ingress.yaml nor virtualservice.yaml. Call from a template that always
renders regardless of mode (service.yaml).
*/}}
{{- define "nexus-ui.validateRoutingMode" -}}
{{- if not (has .Values.routing.mode (list "istio" "nginx")) -}}
{{ fail (printf "routing.mode must be \"istio\" or \"nginx\" — got %q" .Values.routing.mode) }}
{{- end -}}
{{- end -}}
