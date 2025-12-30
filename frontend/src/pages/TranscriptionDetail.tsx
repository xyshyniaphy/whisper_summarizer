import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Container, Title, Text, Paper, Badge, Group, Button, Loader, Stack } from '@mantine/core';
import { api } from '../services/api';
import { Transcription } from '../types';

export function TranscriptionDetail() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [transcription, setTranscription] = useState<Transcription | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (id) {
            loadTranscription(id);
        }
    }, [id]);

    const loadTranscription = async (transcriptionId: string) => {
        try {
            const data = await api.getTranscription(transcriptionId);
            setTranscription(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <Container py="xl"><Loader /></Container>;
    }

    if (!transcription) {
        return <Container py="xl"><Text>見つかりませんでした</Text></Container>;
    }

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
                    <Title order={4} mb="sm">文字起こし結果</Title>
                    <Text style={{ whiteSpace: 'pre-wrap' }}>
                        {transcription.original_text || '文字起こし中、または結果がありません...'}
                    </Text>
                </Paper>

                {/* Placeholder for Summary */}
                <Paper p="md" withBorder radius="md">
                    <Title order={4} mb="sm">AI要約</Title>
                    <Text c="dimmed">要約機能はまだ実装されていません。</Text>
                </Paper>
            </Stack>
        </Container>
    );
}
