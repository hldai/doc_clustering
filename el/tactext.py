import re
import os
import numpy as np

from mention import Mention
import textutils
import ioutils
import dataarange


def __is_full_name(acronym, full_name):
    fpos = 0
    for ch in acronym:
        if not ch.isalpha():
            return False
            # continue

        flg = False
        while fpos < len(full_name) and (not flg):
            if full_name[fpos].isupper():
                if full_name[fpos] == ch:
                    flg = True
                else:
                    break
            fpos += 1
        if not flg:
            return False

    while fpos < len(full_name):
        if full_name[fpos].isupper():
            return False
        fpos += 1

    return True


def __get_doc_id_from_path(docpath):
    beg_pos = docpath.rfind('\\')
    tmp = docpath.rfind('/')
    beg_pos = beg_pos if beg_pos > tmp else tmp
    if docpath.endswith('.nw.xml') or docpath.endswith('.df.xml'):
        return docpath[beg_pos + 1:-7]
    return docpath[beg_pos + 1:-4]


def __load_ner_result(filename, toutf8=True):
    doc_entities = dict()
    f = open(filename, 'r')
    for line in f:
        vals = line.strip().split('\t')
        docid = vals[0]
        num_entities = int(vals[1])
        entities = list()
        for i in xrange(num_entities):
            line = f.next()
            vals = line.strip().split('\t')
            entity_name = vals[0]
            if toutf8:
                entity_name = entity_name.decode('utf-8')
            entities.append((entity_name, vals[1]))
        doc_entities[docid] = entities
    f.close()
    return doc_entities


def __expand_acronym(query_name, entities_in_doc):
    new_name = query_name
    for (name, entity_type) in entities_in_doc:
        # print name, entity_type
        if __is_full_name(query_name, name) and len(name) > len(new_name):
            new_name = name
            # print query_name, new_name
    # if len(entity_name) > len(query_name):
    #                 print '%s\t%s\t%s#%s*' % (query_id, doc_id, query_name, entity_name),
    #                 query_name = entity_name
    #                 exp_cnt += 1
    #                 print '*###',
    #                 print
    return new_name


def __expand_person_name(query_name, entities_in_doc):
    new_name = query_name
    query_name_lc = query_name.lower()
    # print query_name_lc, query_name
    for (name, entity_type) in entities_in_doc:
        if entity_type != 'PERSON':
            continue

        pos = name.lower().find(query_name_lc)
        # if query_name_lc == 'abudllah':
        #     print name, pos
        if pos < 0:
            continue

        left_flg = (pos == 0) or (name[pos - 1] == ' ' or name[pos - 1] == '-')
        rpos = pos + len(query_name_lc)
        right_flg = (rpos == len(name)) or (name[rpos] == ' ' or name[rpos] == '-')

        if left_flg and right_flg and len(name) > len(new_name):
            new_name = name
        # if (len(name) > len(query_name)):
        #     print '%s\t%s' % (query_name, name)
    return new_name


def __find_expansion_candidates_in_location_mentions(mentions, words):
    expansion_candidates = []
    for m in mentions:
        if ' ' in m.name:
            continue
        for i in xrange(len(words) - 2):
            if m.name.lower() != words[i].lower():
                continue
            if words[i + 1] != ',':
                continue
            endpos = i + 2
            while endpos < len(words) and words[endpos][0].isupper():
                endpos += 1
            if endpos > i + 2:
                # print m.name, words[i:endpos]
                exp_name = m.name + ' '.join(words[i + 1:endpos])
                # print '%s\t%s' % (m.name, exp_name)
                expansion_candidates.append((m.mention_id, exp_name))
                if '.' in exp_name:
                    new_exp_name = exp_name.replace('.', '')
                    expansion_candidates.append((m.mention_id, new_exp_name))
    return expansion_candidates


def __filter_expansion_candidates(expansion_candidates, entity_candidates_dict_file):
    name_qids_dict = dict()
    for tup in expansion_candidates:
        qids = name_qids_dict.get(tup[1].lower(), list())
        if not qids:
            name_qids_dict[tup[1].lower()] = qids
        if tup[0] not in qids:
            qids.append(tup[0])
    expansion_dict = dict()
    # for tup in expansion_candidates:
    #     expansion_dict[tup[0]] = tup[1]
    # print len(expansion_dict)

    f = open(entity_candidates_dict_file, 'rb')
    num_names, total_num_cands = np.fromfile(f, '>i4', 2)
    print num_names
    for i in xrange(num_names):
        name = ioutils.read_str_with_byte_len(f)
        # print name
        num_cands = np.fromfile(f, '>i2', 1)
        if num_cands == 0:
            continue

        qids = name_qids_dict.get(name, [])
        for qid in qids:
            expansion_dict[qid] = name

        # print num_cands
        for _ in xrange(num_cands):
            ioutils.read_str_with_byte_len(f)
            np.fromfile(f, '>f4', 1)

        if i % 1000000 == 0:
            print i
    f.close()

    for qid, name in expansion_dict.iteritems():
        print qid, name
    print len(expansion_dict)
    return expansion_dict


def __expand_location_names(mentions, tokenized_text_file, entity_candidates_dict_file):
    doc_mentions_dict = Mention.group_mentions_by_docid(mentions)

    expansion_candidates = []
    f = open(tokenized_text_file, 'r')
    for line in f:
        vals = line.strip().split('\t')
        docid = vals[0]
        # print docid
        num_lines = int(vals[1])
        doc_mentions = doc_mentions_dict[docid]
        # print len(mentions)
        for i in xrange(num_lines):
            line = f.next().decode('utf-8')
            words = line.strip().split(' ')
            expansion_candidates += __find_expansion_candidates_in_location_mentions(doc_mentions, words)
            # break
        # break
    f.close()

    expansion_dict = __filter_expansion_candidates(expansion_candidates, entity_candidates_dict_file)
    qid_mentions = Mention.group_mentions_by_qid(mentions)
    for qid, mention in qid_mentions.iteritems():
        exp_name = expansion_dict.get(qid, '')
        if not exp_name:
            continue
        print '%s\t%s\t%s' % (qid, mention.name, exp_name)
        mention.name = exp_name


def __expand_name_with_ner_result(mentions, doc_ner_file):
    doc_entity_names = __load_ner_result(doc_ner_file)
    for m in mentions:
        cur_doc_entity_names = doc_entity_names[m.docid]
        if m.name.isupper():
            expanded_name = __expand_acronym(m.name, cur_doc_entity_names)
            if len(expanded_name) > len(m.name):
                m.name = expanded_name

        expanded_name = __expand_person_name(m.name, cur_doc_entity_names)
        if len(expanded_name) > len(m.name):
            print '%s\t%s\t%s' % (m.mention_id, m.name, expanded_name)
            m.name = expanded_name


def __name_expansion(edl_mentions_file, doc_ner_file, tokenized_text_file, entity_candidates_dict_file, dst_file):
    mentions = Mention.load_edl_file(edl_mentions_file)
    __expand_name_with_ner_result(mentions, doc_ner_file)
    # __expand_location_names(mentions, tokenized_text_file, entity_candidates_dict_file)
    Mention.save_as_edl_file(mentions, dst_file)


def __gen_line_docs_file_tac(doc_list_file, dst_line_docs_file):
    f = open(doc_list_file, 'r')
    fout = open(dst_line_docs_file, 'wb')
    for line in f:
        line = line.strip()
        print line
        line_text = textutils.doc_to_line(line)
        fout.write(line_text)
        fout.write('\n')
    f.close()
    fout.close()


def __job_init_entity_net():
    line_docs_file_name = 'e:/data/emadr/el/tac/2011/eval/docs-tokenized.txt'
    illegal_start_words_file = 'e:/data/emadr/20ng_bydate/stopwords.txt'
    dst_doc_entity_candidates_list_file = 'e:/data/emadr/el/tac/2011/eval/doc_entity_candidates.txt'
    dst_entity_candidate_clique_file = 'e:/data/emadr/el/tac/2011/eval/entity_candidate_cliques.txt'
    dataarange.init_entity_net(line_docs_file_name, illegal_start_words_file, dst_doc_entity_candidates_list_file,
                               dst_entity_candidate_clique_file)


def __setup_doc_entities_file():
    illegal_start_words_file = 'e:/data/emadr/20ng_bydate/stopwords.txt'

    emadr_data_dir = 'e:/data/emadr/el/tac/2014/eval/'
    line_docs_file = os.path.join(emadr_data_dir, 'docs-tokenized.txt')
    doc_entity_candidates_list_file = os.path.join(emadr_data_dir, 'doc_entity_candidates.txt')
    entity_candidate_clique_file = os.path.join(emadr_data_dir, 'entity_candidate_cliques.txt')
    dataarange.init_entity_net(line_docs_file, illegal_start_words_file, doc_entity_candidates_list_file,
                               entity_candidate_clique_file)

    proper_entity_dict_file = 'e:/data/emadr/el/wiki/entity_names.txt'
    # doc_entity_candidates_file = 'e:/data/emadr/el/wiki/doc_entity_candidates.txt'
    dst_doc_entity_list_file = os.path.join(emadr_data_dir, 'de.bin')

    dataarange.gen_doc_entity_pairs(proper_entity_dict_file, doc_entity_candidates_list_file, dst_doc_entity_list_file)
    # dst_entity_cnts_file = 'e:/data/emadr/el/tac/2011/eval/entity_cnts.bin'
    # textutils.gen_word_cnts_file_from_bow_file(dst_doc_entity_list_file, dst_entity_cnts_file)


def __gen_tac_dw():
    # docs_dir = r'D:\data\el\LDC2015E19\data\2010\training\source_documents'
    # docs_dir = r'D:\data\el\LDC2015E19\data\2010\eval\source_documents'
    # docs_dir = r'D:\data\el\LDC2015E19\data\2009\eval\source_documents'

    # doc_list_file = 'e:/data/el/LDC2015E19/data/2010/eval/data/eng-docs-list-win.txt'
    doc_list_file = 'e:/data/el/LDC2015E20/data/eval/data/eng-docs-list-win.txt'
    emadr_data_dir = 'e:/data/emadr/el/tac/2014/eval'
    line_docs_file = os.path.join(emadr_data_dir, 'docs.txt')
    # __gen_line_docs_file_tac(doc_list_file, line_docs_file)

    tokenized_line_docs_file = os.path.join(emadr_data_dir, 'docs-tokenized.txt')
    proper_word_cnts_dict_file = 'e:/data/emadr/el/wiki/words_dict_proper.txt'
    max_word_len = 20
    tokenized_line_docs_lc_file = os.path.join(emadr_data_dir, 'docs-tokenized-lc.txt')
    bow_docs_file = os.path.join(emadr_data_dir, 'dw.bin')

    textutils.gen_lowercase_token_file(tokenized_line_docs_file, proper_word_cnts_dict_file,
                                       max_word_len, 1, tokenized_line_docs_lc_file)
    min_occurrence = 2
    words_dict = textutils.load_words_to_idx_dict(proper_word_cnts_dict_file, min_occurrence)
    textutils.line_docs_to_bow(tokenized_line_docs_lc_file, words_dict, min_occurrence, bow_docs_file)

    # dst_word_cnts_file = 'e:/data/emadr/el/tac/%d/%s/word_cnts.bin' % (year, part)
    # textutils.gen_word_cnts_file_from_bow_file(bow_docs_file, dst_word_cnts_file)


def __job_name_expansion():
    # query_file = r'e:\data\el\LDC2015E19\data\2011\eval\tac' \
    #              r'_kbp_2011_english_entity_linking_evaluation_queries.xml'
    # dst_query_file = r'e:/data/el/LDC2015E19/data/2011/eval/data/queries-name-expansion.xml'
    # doc_list_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/eng-docs-list-win.txt'
    entity_candidates_dict_file = 'e:/data/edl/res/prog-gen/candidates-dict.bin'

    edl_mentions_file = 'e:/data/el/LDC2015E19/data/2009/eval/data/mentions.tab'
    doc_ner_file = 'e:/data/el/LDC2015E19/data/2009/eval/data/doc-entities-ner.txt'
    tokenized_text_file = 'e:/data/el/LDC2015E19/data/2009/eval/data/doc-text-tokenized.txt'
    dst_file = 'e:/data/el/LDC2015E19/data/2009/eval/data/mentions-expansion-nloc.tab'

    # edl_mentions_file = 'e:/data/el/LDC2015E19/data/2010/eval/data/mentions.tab'
    # doc_ner_file = 'e:/data/el/LDC2015E19/data/2010/eval/data/doc-entities-ner.txt'
    # tokenized_text_file = 'e:/data/el/LDC2015E19/data/2010/eval/data/doc-text-tokenized.txt'
    # dst_file = 'e:/data/el/LDC2015E19/data/2010/eval/data/mentions-expansion-nloc.tab'

    # edl_mentions_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/mentions.tab'
    # doc_ner_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/doc-entities-ner.txt'
    # tokenized_text_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/doc-text-tokenized.txt'
    # dst_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/mentions-all-expansion.tab'
    __name_expansion(edl_mentions_file, doc_ner_file, tokenized_text_file, entity_candidates_dict_file, dst_file)


def __test():
    mention_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/mentions-name-expansion.tab'
    dst_mention_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/mentions-all-expansion.tab'
    tokenized_doc_text_file = 'e:/data/el/LDC2015E19/data/2011/eval/data/doc-text-tokenized.txt'
    candidates_dict_file = 'e:/data/edl/res/prog-gen/candidates-dict.bin'
    # __expand_locations(mention_file, tokenized_doc_text_file, candidates_dict_file, dst_mention_file)

if __name__ == '__main__':
    # __gen_tac_dw()
    __setup_doc_entities_file()
    # gen_doc_mention_names()
    # __job_acronym_expansion()
    # __job_name_expansion()
    # process_docs_for_ner()
    # __test()
