import React, { useState } from 'react';
import { Group, Text, useMantineTheme, rem, Button, Progress, Card } from '@mantine/core';
import { IconUpload, IconPhoto, IconX, IconFileMusic } from '@tabler/icons-react';
import { Dropzone, DropzoneProps, FileWithPath } from '@mantine/dropzone';
import { api } from '../services/api';
import { useNavigate } from 'react-router-dom';

export function AudioUploader() {
    const theme = useMantineTheme();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDrop = async (files: FileWithPath[]) => {
        if (files.length === 0) return;

        setLoading(true);
        setError(null);
        try {
            const file = files[0];
            const transcription = await api.uploadAudio(file);
            navigate(`/transcriptions/${transcription.id}`);
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "アップロードに失敗しました");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card shadow="sm" padding="lg" radius="md" withBorder>
            <Dropzone
                onDrop={handleDrop}
                onReject={(files) => console.log('rejected files', files)}
                maxSize={50 * 1024 ** 2} // 50MB
                accept={['audio/mpeg', 'audio/wav', 'audio/aac', 'audio/flac', 'audio/ogg', 'audio/x-m4a', 'audio/mp4']}
                loading={loading}
            >
                <Group justify="center" gap="xl" style={{ minHeight: rem(220), pointerEvents: 'none' }}>
                    <Dropzone.Accept>
                        <IconUpload
                            style={{ width: rem(52), height: rem(52), color: 'var(--mantine-color-blue-6)' }}
                            stroke={1.5}
                        />
                    </Dropzone.Accept>
                    <Dropzone.Reject>
                        <IconX
                            style={{ width: rem(52), height: rem(52), color: 'var(--mantine-color-red-6)' }}
                            stroke={1.5}
                        />
                    </Dropzone.Reject>
                    <Dropzone.Idle>
                        <IconFileMusic
                            style={{ width: rem(52), height: rem(52), color: 'var(--mantine-color-dimmed)' }}
                            stroke={1.5}
                        />
                    </Dropzone.Idle>

                    <div>
                        <Text size="xl" inline>
                            音声ファイルをここにドラッグ&ドロップ
                        </Text>
                        <Text size="sm" c="dimmed" inline mt={7}>
                            またはクリックしてファイルを選択 (mp3, wav, m4a, etc)
                        </Text>
                    </div>
                </Group>
            </Dropzone>
            {error && <Text c="red" mt="sm">{error}</Text>}
        </Card>
    );
}
