import React, { useEffect, useState } from 'react';
import { Title, Container, Table, Badge, Button, Group, Text, Card } from '@mantine/core';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Transcription } from '../types';
import { AudioUploader } from '../components/AudioUploader';

export function TranscriptionList() {
    const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
    const navigate = useNavigate();

    useEffect(() => {
        loadTranscriptions();
    }, []);

    const loadTranscriptions = async () => {
        try {
            const data = await api.getTranscriptions();
            setTranscriptions(data);
        } catch (e) {
            console.error(e);
        }
    };

    const rows = transcriptions.map((item) => (
        <Table.Tr key={item.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/transcriptions/${item.id}`)}>
            <Table.Td>{item.file_name}</Table.Td>
            <Table.Td>
                <Badge
                    color={item.status === 'completed' ? 'green' : item.status === 'failed' ? 'red' : 'blue'}
                >
                    {item.status}
                </Badge>
            </Table.Td>
            <Table.Td>{new Date(item.created_at).toLocaleString()}</Table.Td>
        </Table.Tr>
    ));

    return (
        <Container size="lg" py="xl">
            <Title order={2} mb="lg">新しい文字起こし</Title>
            <AudioUploader />

            <Title order={2} mt="xl" mb="md">文字起こし履歴</Title>
            <Card withBorder radius="md">
                <Table highlightOnHover>
                    <Table.Thead>
                        <Table.Tr>
                            <Table.Th>ファイル名</Table.Th>
                            <Table.Th>ステータス</Table.Th>
                            <Table.Th>作成日時</Table.Th>
                        </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>{rows}</Table.Tbody>
                </Table>
                {transcriptions.length === 0 && (
                    <Text ta="center" py="xl" c="dimmed">データがありません</Text>
                )}
            </Card>
        </Container>
    );
}
