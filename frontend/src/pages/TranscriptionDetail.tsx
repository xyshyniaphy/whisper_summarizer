import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Title, Text, Paper, Badge, Group, Button, Loader, Stack } from '@mantine/core';
import { IconDownload, IconSparkles } from '@tabler/icons-react';
import { api } from '../services/api';
import { Transcription, Summary } from '../types';

// 表示用に最初の200行を取得
const getDisplayText = (text: string, maxLines: number = 200): string => {
    const lines = text.split('\n');
    if (lines.length <= maxLines) {
        return text;
    }
    return lines.slice(0, maxLines).join('\n') +
        `\n\n... (残り ${lines.length - maxLines} 行。完全版はダウンロードしてください)`;
};

export function TranscriptionDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [transcription, setTranscription] = useState<Transcription | null>(null);
    const [summary, setSummary] = useState<Summary | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadingSummary, setLoadingSummary] = useState(false);

    useEffect(() => {
        if (id) {
            loadTranscription(id);
        }
    }, [id]);

    const loadTranscription = async (transcriptionId: string) => {
        try {
            const data = await api.getTranscription(transcriptionId);
            setTranscription(data);

            // 既存の要約があれば取得
            if (data.summaries && data.summaries.length > 0) {
                setSummary(data.summaries[0]);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateSummary = async () => {
        if (!id) return;

        setLoadingSummary(true);
        try {
            const result = await api.generateSummary(id);
            setSummary(result);
        } catch (error) {
            console.error('要約生成エラー:', error);
        } finally {
            setLoadingSummary(false);
        }
    };

    if (loading) {
        return <Container py="xl"><Loader /></Container>;
    }

    if (!transcription) {
        return <Container py="xl"><Text>見つかりませんでした</Text></Container>;
    }

    const displayText = transcription.original_text
        ? getDisplayText(transcription.original_text, 200)
        : '文字起こし中、または結果がありません...';

    const downloadUrlTxt = api.getDownloadUrl(transcription.id, 'txt');
    const downloadUrlSrt = api.getDownloadUrl(transcription.id, 'srt');

    return (
        <Container size="lg" py="xl">
            <Button variant="subtle" mb="md" onClick={() => navigate('/transcriptions')}>
                &larr; 一覧に戻る
            </Button>

            <Group justify="space-between" mb="lg">
                <Title order={2}>{transcription.file_name}</Title>
                <Badge
                    size="lg"
                    color={transcription.status === 'completed' ? 'green' : transcription.status === 'failed' ? 'red' : 'blue'}
                >
                    {transcription.status}
                </Badge>
            </Group>

            <Stack gap="lg">
                <Paper p="md" withBorder radius="md">
                    <Group justify="space-between" mb="sm">
                        <Title order={4}>文字起こし結果</Title>
                        {transcription.status === 'completed' && (
                            <Group gap="xs">
                                <Button
                                    component="a"
                                    href={downloadUrlTxt}
                                    download
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconDownload size={16} />}
                                >
                                    テキストをダウンロード
                                </Button>
                                <Button
                                    component="a"
                                    href={downloadUrlSrt}
                                    download
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconDownload size={16} />}
                                >
                                    字幕（SRT）をダウンロード
                                </Button>
                            </Group>
                        )}
                    </Group>
                    <Text style={{ whiteSpace: 'pre-wrap' }}>
                        {displayText}
                    </Text>
                </Paper>

                <Paper p="md" withBorder radius="md">
                    <Group justify="space-between" mb="sm">
                        <Title order={4}>AI要約</Title>
                        {transcription.status === 'completed' && !summary && (
                            <Button
                                onClick={handleGenerateSummary}
                                loading={loadingSummary}
                                size="sm"
                                leftSection={<IconSparkles size={18} />}
                            >
                                要約を生成
                            </Button>
                        )}
                    </Group>
                    {summary ? (
                        <Text style={{ whiteSpace: 'pre-wrap' }}>
                            {summary.summary_text}
                        </Text>
                    ) : (
                        <Text c="dimmed">
                            {transcription.status === 'completed'
                                ? '「要約を生成」ボタンをクリックして要約を作成してください。'
                                : '文字起こしが完了すると要約を生成できます。'}
                        </Text>
                    )}
                </Paper>
            </Stack>
        </Container>
    );
}
