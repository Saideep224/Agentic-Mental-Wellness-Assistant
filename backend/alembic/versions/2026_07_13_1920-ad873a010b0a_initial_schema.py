"""initial_schema

Revision ID: ad873a010b0a
Revises: None
Create Date: 2026-07-13 19:20:34.023438+00:00

"""
from alembic import op
import sqlalchemy as sa
import app.database

# revision identifiers, used by Alembic.
revision = 'ad873a010b0a'
down_revision = None
branch_labels = None
depends_on = None


def table_exists(name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return name in inspector.get_table_names()


def get_missing_columns(table_name, expected_columns):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = [c['name'] for c in inspector.get_columns(table_name)]
    return {name: col for name, col in expected_columns.items() if name not in existing_cols}


def index_exists(table_name, index_name):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name) if idx['name'] is not None]
    return index_name in indexes


def upgrade():
    # ── 1. profiles ───────────────────────────────────────────────────────────
    profiles_cols = {
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'email': sa.Column('email', sa.String(length=320), nullable=False),
        'full_name': sa.Column('full_name', sa.String(length=255), nullable=False),
        'avatar_url': sa.Column('avatar_url', sa.String(length=1024), nullable=True),
        'provider': sa.Column('provider', sa.String(length=50), nullable=False),
        'github_username': sa.Column('github_username', sa.String(length=255), nullable=True),
        'onboarding_completed': sa.Column('onboarding_completed', sa.Boolean(), nullable=False),
        'onboarding_step': sa.Column('onboarding_step', sa.Integer(), nullable=True),
        'personality_profile': sa.Column('personality_profile', sa.JSON(), nullable=True),
        'interests': sa.Column('interests', sa.JSON(), nullable=True),
        'communication_style': sa.Column('communication_style', sa.Text(), nullable=True),
        'personality_type': sa.Column('personality_type', sa.Text(), nullable=True),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        'last_login': sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    }

    if not table_exists('profiles'):
        op.create_table(
            'profiles',
            *profiles_cols.values(),
            sa.PrimaryKeyConstraint('user_id'),
            sa.UniqueConstraint('id')
        )
    else:
        missing = get_missing_columns('profiles', profiles_cols)
        for name, col in missing.items():
            op.add_column('profiles', col)

    if not index_exists('profiles', 'ix_profiles_email'):
        op.create_index(op.f('ix_profiles_email'), 'profiles', ['email'], unique=True)
    if not index_exists('profiles', 'ix_profiles_user_id'):
        op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=False)

    # ── 2. conversations ──────────────────────────────────────────────────────
    conversations_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'title': sa.Column('title', sa.String(length=512), nullable=False),
        'agent_id': sa.Column('agent_id', sa.String(length=50), server_default='buddy', nullable=False),
        'active_specialists': sa.Column('active_specialists', sa.JSON(), server_default='[]', nullable=True),
        'emotional_tag': sa.Column('emotional_tag', sa.String(length=255), nullable=True),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('conversations'):
        op.create_table(
            'conversations',
            *conversations_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('conversations', conversations_cols)
        for name, col in missing.items():
            op.add_column('conversations', col)

    if not index_exists('conversations', 'ix_conversations_user_id'):
        op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'], unique=False)

    # ── 3. emotion_logs ───────────────────────────────────────────────────────
    emotion_logs_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'message': sa.Column('message', sa.Text(), nullable=False),
        'detected_emotion': sa.Column('detected_emotion', sa.String(length=100), nullable=False),
        'confidence_score': sa.Column('confidence_score', sa.Float(), nullable=False),
        'secondary_emotion': sa.Column('secondary_emotion', sa.String(length=100), nullable=True),
        'timestamp': sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('emotion_logs'):
        op.create_table(
            'emotion_logs',
            *emotion_logs_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('emotion_logs', emotion_logs_cols)
        for name, col in missing.items():
            op.add_column('emotion_logs', col)

    if not index_exists('emotion_logs', 'ix_emotion_logs_user_id'):
        op.create_index(op.f('ix_emotion_logs_user_id'), 'emotion_logs', ['user_id'], unique=False)

    # ── 4. knowledge_graph ────────────────────────────────────────────────────
    knowledge_graph_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'subject': sa.Column('subject', sa.String(length=255), nullable=False),
        'predicate': sa.Column('predicate', sa.String(length=255), nullable=False),
        'object': sa.Column('object', sa.String(length=255), nullable=False),
        'confidence': sa.Column('confidence', sa.Float(), nullable=False),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('knowledge_graph'):
        op.create_table(
            'knowledge_graph',
            *knowledge_graph_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('knowledge_graph', knowledge_graph_cols)
        for name, col in missing.items():
            op.add_column('knowledge_graph', col)

    if not index_exists('knowledge_graph', 'ix_knowledge_graph_user_id'):
        op.create_index(op.f('ix_knowledge_graph_user_id'), 'knowledge_graph', ['user_id'], unique=False)

    # ── 5. memories ───────────────────────────────────────────────────────────
    memories_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'memory_content': sa.Column('memory_content', sa.Text(), nullable=False),
        'memory_type': sa.Column('memory_type', sa.String(length=100), nullable=True),
        'importance_score': sa.Column('importance_score', sa.Float(), nullable=True),
        'behavior_patterns': sa.Column('behavior_patterns', sa.JSON(), nullable=False),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('memories'):
        op.create_table(
            'memories',
            *memories_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('memories', memories_cols)
        for name, col in missing.items():
            op.add_column('memories', col)

    if not index_exists('memories', 'ix_memories_user_id'):
        op.create_index(op.f('ix_memories_user_id'), 'memories', ['user_id'], unique=False)

    # ── 6. mood_logs ──────────────────────────────────────────────────────────
    mood_logs_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'mood_score': sa.Column('mood_score', sa.Float(), nullable=False),
        'mood_label': sa.Column('mood_label', sa.String(length=100), nullable=False),
        'detected_emotion': sa.Column('detected_emotion', sa.String(length=100), nullable=False),
        'stress': sa.Column('stress', sa.Float(), nullable=True),
        'happiness': sa.Column('happiness', sa.Float(), nullable=True),
        'sadness': sa.Column('sadness', sa.Float(), nullable=True),
        'anxiety': sa.Column('anxiety', sa.Float(), nullable=True),
        'motivation': sa.Column('motivation', sa.Float(), nullable=True),
        'confidence': sa.Column('confidence', sa.Float(), nullable=True),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('mood_logs'):
        op.create_table(
            'mood_logs',
            *mood_logs_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('mood_logs', mood_logs_cols)
        for name, col in missing.items():
            op.add_column('mood_logs', col)

    if not index_exists('mood_logs', 'ix_mood_logs_user_id'):
        op.create_index(op.f('ix_mood_logs_user_id'), 'mood_logs', ['user_id'], unique=False)

    # ── 7. user_entities ──────────────────────────────────────────────────────
    user_entities_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'entity': sa.Column('entity', sa.String(length=255), nullable=False),
        'type': sa.Column('type', sa.String(length=255), nullable=False),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('user_entities'):
        op.create_table(
            'user_entities',
            *user_entities_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('user_entities', user_entities_cols)
        for name, col in missing.items():
            op.add_column('user_entities', col)

    if not index_exists('user_entities', 'ix_user_entities_user_id'):
        op.create_index(op.f('ix_user_entities_user_id'), 'user_entities', ['user_id'], unique=False)

    # ── 8. user_personality ───────────────────────────────────────────────────
    user_personality_cols = {
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'personality_profile': sa.Column('personality_profile', sa.JSON(), nullable=False),
        'personality_type': sa.Column('personality_type', sa.JSON(), nullable=False),
        'communication_style': sa.Column('communication_style', sa.JSON(), nullable=False),
        'interests': sa.Column('interests', sa.JSON(), nullable=False),
        'stress_indicators': sa.Column('stress_indicators', sa.JSON(), nullable=False),
        'personality_type_dict': sa.Column('personality_type_dict', sa.JSON(), nullable=False),
        'emotional_style': sa.Column('emotional_style', sa.JSON(), nullable=False),
        'stress_triggers': sa.Column('stress_triggers', sa.JSON(), nullable=False),
        'strengths': sa.Column('strengths', sa.JSON(), nullable=False),
        'weaknesses': sa.Column('weaknesses', sa.JSON(), nullable=False),
        'onboarding_answers': sa.Column('onboarding_answers', sa.JSON(), nullable=False),
        'onboarding_completed': sa.Column('onboarding_completed', sa.Boolean(), nullable=False),
        'emotional_baseline': sa.Column('emotional_baseline', sa.JSON(), nullable=False),
        'comfort_preferences': sa.Column('comfort_preferences', sa.JSON(), nullable=False),
        'emotional_summary': sa.Column('emotional_summary', sa.JSON(), nullable=False),
        'stress_patterns': sa.Column('stress_patterns', sa.JSON(), nullable=False),
        'emotional_triggers': sa.Column('emotional_triggers', sa.JSON(), nullable=False),
        'preferred_response_style': sa.Column('preferred_response_style', sa.JSON(), nullable=False),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('user_personality'):
        op.create_table(
            'user_personality',
            *user_personality_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id')
        )
    else:
        missing = get_missing_columns('user_personality', user_personality_cols)
        for name, col in missing.items():
            op.add_column('user_personality', col)

    if not index_exists('user_personality', 'ix_user_personality_user_id'):
        op.create_index(op.f('ix_user_personality_user_id'), 'user_personality', ['user_id'], unique=False)

    # ── 9. user_profile ───────────────────────────────────────────────────────
    user_profile_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'name': sa.Column('name', sa.String(length=255), nullable=True),
        'age': sa.Column('age', sa.String(length=50), nullable=True),
        'profession': sa.Column('profession', sa.String(length=255), nullable=True),
        'field_of_work': sa.Column('field_of_work', sa.String(length=255), nullable=True),
        'university': sa.Column('university', sa.String(length=255), nullable=True),
        'current_challenge': sa.Column('current_challenge', sa.String(length=255), nullable=True),
        'advice_preference': sa.Column('advice_preference', sa.String(length=255), nullable=True),
        'primary_support_need': sa.Column('primary_support_need', sa.String(length=255), nullable=True),
        'student_year': sa.Column('student_year', sa.String(length=100), nullable=True),
        'communication_style': sa.Column('communication_style', sa.String(length=100), nullable=True),
        'interests': sa.Column('interests', sa.JSON(), nullable=False),
        'hobbies': sa.Column('hobbies', sa.JSON(), nullable=False),
        'goals': sa.Column('goals', sa.JSON(), nullable=False),
        'stress_triggers': sa.Column('stress_triggers', sa.JSON(), nullable=False),
        'coping_mechanisms': sa.Column('coping_mechanisms', sa.JSON(), nullable=False),
        'support_system': sa.Column('support_system', sa.Text(), nullable=True),
        'sleep_habits': sa.Column('sleep_habits', sa.String(length=100), nullable=True),
        'gender': sa.Column('gender', sa.String(length=50), nullable=True),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('user_profile'):
        op.create_table(
            'user_profile',
            *user_profile_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('user_profile', user_profile_cols)
        for name, col in missing.items():
            op.add_column('user_profile', col)

    if not index_exists('user_profile', 'ix_user_profile_user_id'):
        op.create_index(op.f('ix_user_profile_user_id'), 'user_profile', ['user_id'], unique=True)

    # ── 10. user_question_answers ─────────────────────────────────────────────
    user_question_answers_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'question_id': sa.Column('question_id', sa.Integer(), nullable=False),
        'question_text': sa.Column('question_text', sa.Text(), nullable=False),
        'category': sa.Column('category', sa.String(length=100), nullable=False),
        'selected_answer': sa.Column('selected_answer', sa.JSON(), nullable=False),
        'custom_answer': sa.Column('custom_answer', sa.Text(), nullable=True),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        'updated_at': sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('user_question_answers'):
        op.create_table(
            'user_question_answers',
            *user_question_answers_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'question_id', name='uq_user_question_answers_user_question')
        )
    else:
        missing = get_missing_columns('user_question_answers', user_question_answers_cols)
        for name, col in missing.items():
            op.add_column('user_question_answers', col)

    if not index_exists('user_question_answers', 'ix_user_question_answers_user_id'):
        op.create_index(op.f('ix_user_question_answers_user_id'), 'user_question_answers', ['user_id'], unique=False)

    # ── 11. user_relationships ────────────────────────────────────────────────
    user_relationships_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'source': sa.Column('source', sa.String(length=255), nullable=False),
        'relationship': sa.Column('relationship', sa.String(length=255), nullable=False),
        'target': sa.Column('target', sa.String(length=255), nullable=False),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('user_relationships'):
        op.create_table(
            'user_relationships',
            *user_relationships_cols.values(),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('user_relationships', user_relationships_cols)
        for name, col in missing.items():
            op.add_column('user_relationships', col)

    if not index_exists('user_relationships', 'ix_user_relationships_user_id'):
        op.create_index(op.f('ix_user_relationships_user_id'), 'user_relationships', ['user_id'], unique=False)

    # ── 12. chat_messages ─────────────────────────────────────────────────────
    chat_messages_cols = {
        'id': sa.Column('id', app.database.SafeUUID(), nullable=False),
        'conversation_id': sa.Column('conversation_id', app.database.SafeUUID(), nullable=False),
        'user_id': sa.Column('user_id', app.database.SafeUUID(), nullable=False),
        'role': sa.Column('role', sa.Enum('user', 'assistant', name='message_role', create_constraint=True), nullable=False),
        'message': sa.Column('message', sa.Text(), nullable=False),
        'emotion': sa.Column('emotion', sa.String(length=100), nullable=True),
        'mood_score': sa.Column('mood_score', sa.Float(), nullable=True),
        'emotion_score': sa.Column('emotion_score', sa.Float(), nullable=True),
        'stress_score': sa.Column('stress_score', sa.Float(), nullable=True),
        'anxiety_score': sa.Column('anxiety_score', sa.Float(), nullable=True),
        'sender_type': sa.Column('sender_type', sa.String(length=50), server_default='user', nullable=True),
        'agent_analysis': sa.Column('agent_analysis', sa.JSON(), nullable=True),
        'emotional_context': sa.Column('emotional_context', sa.JSON(), nullable=True),
        'created_at': sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    }

    if not table_exists('chat_messages'):
        op.create_table(
            'chat_messages',
            *chat_messages_cols.values(),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['profiles.user_id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
    else:
        missing = get_missing_columns('chat_messages', chat_messages_cols)
        for name, col in missing.items():
            op.add_column('chat_messages', col)

    if not index_exists('chat_messages', 'ix_chat_messages_conversation_id'):
        op.create_index(op.f('ix_chat_messages_conversation_id'), 'chat_messages', ['conversation_id'], unique=False)
    if not index_exists('chat_messages', 'ix_chat_messages_user_id'):
        op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'], unique=False)

    # ── 13. Backfill emotion from detected_emotion ────────────────────────────
    # Guard with try/except to handle case where detected_emotion is not present
    try:
        conn = op.get_bind()
        inspector = sa.inspect(conn)
        existing_cols = [c['name'] for c in inspector.get_columns('chat_messages')]
        
        if 'detected_emotion' in existing_cols and 'emotion' in existing_cols:
            if conn.dialect.name == 'postgresql':
                op.execute("""
                    DO $$
                    BEGIN
                        UPDATE chat_messages 
                        SET emotion = detected_emotion 
                        WHERE emotion IS NULL AND detected_emotion IS NOT NULL;
                    END $$;
                """)
            else:
                op.execute("""
                    UPDATE chat_messages 
                    SET emotion = detected_emotion 
                    WHERE emotion IS NULL 
                    AND detected_emotion IS NOT NULL;
                """)
    except Exception:
        pass  # Safe fallback if backfill table/columns are missing

    # ── 14. user_question_answers check constraint update ─────────────────────
    try:
        # Drop constraint safely first
        op.execute("ALTER TABLE user_question_answers DROP CONSTRAINT IF EXISTS user_question_answers_question_id_check;")
    except Exception:
        pass
    try:
        # Re-add with 1..27 range validation check
        op.create_check_constraint(
            "user_question_answers_question_id_check",
            "user_question_answers",
            "question_id BETWEEN 1 AND 27"
        )
    except Exception:
        pass


def downgrade():
    # Idempotent downgrade: drop only if they exist
    if table_exists('chat_messages'):
        op.drop_table('chat_messages')
    if table_exists('user_relationships'):
        op.drop_table('user_relationships')
    if table_exists('user_question_answers'):
        op.drop_table('user_question_answers')
    if table_exists('user_profile'):
        op.drop_table('user_profile')
    if table_exists('user_personality'):
        op.drop_table('user_personality')
    if table_exists('user_entities'):
        op.drop_table('user_entities')
    if table_exists('mood_logs'):
        op.drop_table('mood_logs')
    if table_exists('memories'):
        op.drop_table('memories')
    if table_exists('knowledge_graph'):
        op.drop_table('knowledge_graph')
    if table_exists('emotion_logs'):
        op.drop_table('emotion_logs')
    if table_exists('conversations'):
        op.drop_table('conversations')
    if table_exists('profiles'):
        op.drop_table('profiles')
